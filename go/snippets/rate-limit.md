---
id: go-rate-limit
title: "Go: rate limiting (token bucket) и ограничение параллельности"
lang: go
min_version: "1.22"
category: snippet
tags: [rate-limit, ratelimiting, throttling, http, "429", retry-after, backpressure]
status: stable
updated: 2026-11-24
---

# Rate limiting и backpressure (Go)

**Когда использовать** — вход в сервис (не дать одному клиенту вынести общий
пул соединений) и выход (не вынести провайдера, у которого лимит на одновременные
вызовы).
**Когда НЕ использовать** — распределённый лимит на несколько подов: token bucket в
памяти процесса не видит соседей, там нужен счётчик в Redis
([../../database/snippets/redis.md](../../database/snippets/redis.md)) или лимит на балансировщике.

## Ограничение частоты (вход)

```go
// Package limiter — ограничение частоты запросов (token bucket).
package limiter

import (
	"net/http"
	"sync"
	"time"

	"golang.org/x/time/rate"
)

// Limiters — лимитеры по ключу (tenant, IP, API-ключ).
// Ключи чистятся: карта без eviction — утечка памяти на каждом новом IP.
type Limiters struct {
	mu      sync.Mutex
	entries map[string]*entry
	rps     rate.Limit
	burst   int
	idle    time.Duration
}

type entry struct {
	*rate.Limiter
	lastSeen time.Time
}

// New: rps — устойчивая скорость на ключ, burst — допуск всплеска.
func New(rps float64, burst int, idle time.Duration) *Limiters {
	return &Limiters{
		entries: make(map[string]*entry),
		rps:     rate.Limit(rps),
		burst:   burst,
		idle:    idle,
	}
}

// Allow — есть ли разрешение на один запрос для ключа.
func (l *Limiters) Allow(key string) bool {
	l.mu.Lock()
	e, ok := l.entries[key]
	if !ok {
		e = &entry{Limiter: rate.NewLimiter(l.rps, l.burst)}
		l.entries[key] = e
	}
	e.lastSeen = time.Now()
	l.mu.Unlock()

	return e.Allow()
}

// EvictIdle убирает лимитеры, которыми не пользовались дольше idle.
// Вызывать из фонового цикла, а не из Allow: там это O(n) под мьютексом.
func (l *Limiters) EvictIdle() int {
	l.mu.Lock()
	defer l.mu.Unlock()

	cutoff := time.Now().Add(-l.idle)
	removed := 0
	for k, e := range l.entries {
		if e.lastSeen.Before(cutoff) {
			delete(l.entries, k)
			removed++
		}
	}
	return removed
}

// Middleware — 429 + Retry-After, когда разрешение не выбрано.
func (l *Limiters) Middleware(keyOf func(*http.Request) string, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		key := keyOf(r)
		if key == "" {
			key = "anonymous" // не «пустой ключ на всех», у кого ключ не определился
		}
		if !l.Allow(key) {
			w.Header().Set("Retry-After", "1")
			http.Error(w, "limit exceeded", http.StatusTooManyRequests)
			return
		}
		next.ServeHTTP(w, r)
	})
}
```

## Ограничение параллельности (выход)

```go
package limiter

import "context"

// Gate — сколько одновременных вызовов наружу (HTTP API, БД) от этого процесса.
// Отдельно от частоты: 100 rps при 500 висящих ответах дообьют провайдера.
type Gate struct {
	slots chan struct{}
}

// NewGate: n — максимум одновременных вызовов; меньше одного не бывает.
func NewGate(n int) *Gate {
	if n < 1 {
		n = 1
	}
	return &Gate{slots: make(chan struct{}, n)}
}

// Do ждёт слота и выполняет fn. ctx отменяет ожидание, слот возвращается всегда.
func (g *Gate) Do(ctx context.Context, fn func() error) error {
	select {
	case g.slots <- struct{}{}:
		defer func() { <-g.slots }()
	case <-ctx.Done():
		return ctx.Err()
	}
	return fn()
}
```

## Pitfalls

- Лимитер в процессной памяти за балансерами: каждый под даёт свой лимит, суммарно —
  `rps × реплики`. Либо миритесь и делите rps на число реплик, либо внешний счётчик.
- Карта лимитеров без `EvictIdle` — медленная утечка: ключом был IP, а IP конечны только
  в вашей сети.
- Забыли `Retry-After` — хороший клиент (и ваш собственный ретрающий код) долбит
  429 без паузы; с заголовком он отступает.
- `429` без различения «лимит» и «перегрузка» — для перегрузки уместнее `503` с
  `Retry-After`, иначе клиент считает, что «кончились квоты», и не ретраит.
- Лимит по IP за прокси: берите адрес из `X-Forwarded-For` только у доверенного
  балансера, иначе ключ подделывается и лимит обходится.
- Один лимит на «всех анонимов» и на авторизованных: боты съедают квоту реальных
  пользователей. Ключ — tenant/API-ключ, анонимов — отдельным, более жёстким лимитером.
- `Gate` без отмены: `ctx.Done()` не проверяется, и очередь слотов превращается
  в очередь висящих запросов при деградации провайдера.

## Related

- [http-server.md](http-server.md) — куда вешать middleware
- [context.md](context.md) — отмена и дедлайны
- [patterns/http-middleware.md](../patterns/http-middleware.md) — порядок middleware
- [../../database/snippets/redis.md](../../database/snippets/redis.md) — распределённый лимит
