---
id: database-redis
title: "Redis: кэширование, структуры данных, TTL"
lang: database
min_version: "8"
category: snippet
tags: [redis, caching, cache-aside, ttl, data-structures, streams]
status: stable
updated: 2026-11-24
---

# Redis: кэш и структуры данных

**Когда использовать** — кэш read-heavy, сессии, счётчики, лёгкие очереди, rate limiting.
**Когда НЕ использовать** — как единственное хранилище критичных данных (Redis — не источник истины).

## Cache-aside (базовый паттерн)

```go
// Package cache — cache-aside: читаем из Redis, пишем в БД, инвалидируем после записи.
package cache

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"time"

	"github.com/redis/go-redis/v9"
)

// User — пример кэшируемой сущности.
type User struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

// rdb — один общий клиент на процесс: пул соединений уже внутри.
var rdb = redis.NewClient(&redis.Options{Addr: "localhost:6379"})

const userTTL = 10 * time.Minute // TTL обязателен: без него устаревшие данные навсегда

// dbUser, dbSaveUser — доступ к источнику истины (БД). Здесь заглушки: пример
// про паттерн кэша, а не про слой хранилища.
func dbUser(_ context.Context, _ string) (User, error) { return User{}, nil }
func dbSaveUser(_ context.Context, _ User) error       { return nil }

func GetUser(ctx context.Context, id string) (User, error) {
	key := "user:" + id
	b, err := rdb.Get(ctx, key).Bytes()
	switch {
	case err == nil:
		var u User
		if err := json.Unmarshal(b, &u); err == nil {
			return u, nil
		}
		// Битое значение в кэше — лечится так же, как промах.
	case !errors.Is(err, redis.Nil):
		// Redis лежит — работаем от БД, но молча превращать сбой в промах нельзя.
		slog.Warn("cache get failed", "key", key, "err", err)
	}

	u, err := dbUser(ctx, id)
	if err != nil {
		return User{}, err
	}
	if b, err := json.Marshal(u); err == nil {
		if err := rdb.Set(ctx, key, b, userTTL).Err(); err != nil {
			slog.Warn("cache set failed", "key", key, "err", err) // не отказ клиенту
		}
	}
	return u, nil
}

func UpdateUser(ctx context.Context, u User) error {
	if err := dbSaveUser(ctx, u); err != nil {
		return err
	}
	// Инвалидация после записи. Упавшая инвалидация = устаревшие данные до истечения
	// TTL, поэтому её видно в логах; для критичных сущностей — ретрай или dual delete.
	if err := rdb.Del(ctx, "user:"+u.ID).Err(); err != nil {
		slog.Error("cache invalidate failed", "key", "user:"+u.ID, "err", err)
	}
	return nil
}
```

## Правила кэша

1. **TTL — всегда** (5–30 мин): без TTL — устаревшие данные навсегда.
2. **Инвалидация после записи** (не до): запись в БД → `DEL`.
3. **Ключи — именованные пространства**: `user:42`, `order:idx:status:unpaid`.
4. **Не кэшируйте «всё»**: только read-heavy + дорогие запросы.
5. **Ошибки кэша видны** (`redis.Nil` — промах, остальное — сбой, см. лог выше).
6. **Cache stampede** (пробой при истечении): на короткий срок — mutex/lock на пересчёт
   (`SET key lock NX EX 5`) или stale-while-revalidate.
7. **Размер значения**: < 10KB; большие — сжать или не кэшировать.

## Структуры данных

| Структура | Команды | Применение |
|---|---|---|
| String | `GET/SET/INCR` | кэш, счётчики, флаги |
| Hash | `HSET/HGETALL` | объект по полям (пользователь) |
| List | `LPUSH/BRPOP` | простая очередь (FIFO) |
| Set | `SADD/SMEMBERS` | уникальные множества, теги |
| Sorted Set | `ZADD/ZRANGEBYSCORE` | топы, очереди по приоритету, rate limit |
| Stream | `XADD/XREADGROUP` | надёжная очередь с группами потребителей |

```go
package rl

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

// ErrRateLimited — отказ по лимиту (HTTP 429).
var ErrRateLimited = errors.New("rate limit exceeded")

var rdb = redis.NewClient(&redis.Options{Addr: "localhost:6379"})

// Limit — скользящее окно на sorted set: key = "rl:user:42", score = время
// запроса, member = уникальный id запроса (один запрос — один элемент).
func Limit(ctx context.Context, key, reqID string, window time.Duration, limit int64) error {
	now := time.Now()
	pipe := rdb.TxPipeline()
	pipe.ZAdd(ctx, key, redis.Z{Score: float64(now.UnixNano()) / 1e9, Member: reqID})
	pipe.ZRemRangeByScore(ctx, key, "-inf", fmt.Sprint(float64(now.Add(-window).UnixNano())/1e9))
	count := pipe.ZCard(ctx, key)
	// Ключ живёт чуть дольше окна, иначе счёт обнуляется вместе с ключом.
	pipe.Expire(ctx, key, window+time.Minute)
	if _, err := pipe.Exec(ctx); err != nil {
		return err
	}
	if count.Val() > limit {
		return ErrRateLimited
	}
	return nil
}
```

## Ошибки

- ❌ «Данные живут только в Redis» — потеря при сбое (RDB/AOF не гарантия).
- ❌ `KEYS *` в production — `SCAN`.
- ❌ Горячий ключ (один key на весь трафик) — шардирование (`user:{shard}:42`).
- ❌ Блокирующие операции в критичном пути (`SMEMBERS` на большом сете).
- ✅ Мониторинг: `used_memory`, `evicted_keys`, `rejected_connections`, hit-rate кэша.

## Related

- [decisions.md — кэширование](../decisions.md)
- [messaging/](../../messaging/) — когда нужен настоящий брокер
