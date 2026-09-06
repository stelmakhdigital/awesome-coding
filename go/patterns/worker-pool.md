---
id: go-worker-pool
title: Worker Pool (ограниченный параллелизм)
lang: go
min_version: "1.20"
category: pattern
tags: [concurrency, workers, pool, errgroup]
status: stable
updated: 2026-09-06
---

# Worker Pool

**Проблема** — N задач нужно выполнить параллельно, но не все сразу: ограничение по памяти, лимиты API, CPU.
**Решение** — фиксированное число воркеров + очередь задач; либо `errgroup.SetLimit` (1.20+) для «map с лимитом».
**Когда использовать** — параллельная обработка с ограничением.
**Когда НЕ использовать** — когда задач мало или они тривиальные: просто цикл.

## Код

```go
package pool

import (
	"context"
	"fmt"
	"sync"

	"golang.org/x/sync/errgroup"
)

// Вариант 1: errgroup.SetLimit — «параллельный map с лимитом».
// Простой, достаточно для большинства случаев.
func MapLimit[T, R any](ctx context.Context, limit int, items []T,
	f func(context.Context, T) (R, error),
) ([]R, error) {
	g, gctx := errgroup.WithContext(ctx)
	g.SetLimit(limit)
	results := make([]R, len(items))
	for i, item := range items {
		i, item := i, item
		g.Go(func() error {
			v, err := f(gctx, item)
			if err != nil {
				return fmt.Errorf("item %d: %w", i, err)
			}
			results[i] = v
			return nil
		})
	}
	if err := g.Wait(); err != nil {
		return nil, err
	}
	return results, nil
}

// Вариант 2: явный пул с каналами — когда нужен контроль над очередью,
// backpressure, приоритетами или живыми воркерами.
type Pool[T, R any] struct {
	workers int
	jobs    chan T
	results chan R
	err     chan error
	wg      sync.WaitGroup
}

func NewPool[T, R any](workers int, f func(context.Context, T) (R, error), ctx context.Context) *Pool[T, R] {
	p := &Pool[T, R]{
		workers: workers,
		jobs:    make(chan T),
		results: make(chan R),
		err:     make(chan error, 1),
	}
	for i := 0; i < workers; i++ {
		p.wg.Add(1)
		go p.worker(ctx, f)
	}
	// Единственный closer: все воркеры завершены.
	go func() {
		p.wg.Wait()
		close(p.results)
	}()
	return p
}

func (p *Pool[T, R]) worker(ctx context.Context, f func(context.Context, T) (R, error)) {
	defer p.wg.Done()
	for job := range p.jobs {
		select {
		case <-ctx.Done():
			return
		default:
		}
		r, err := f(ctx, job)
		if err != nil {
			select {
			case p.err <- err:
			default:
			}
			return
		}
		p.results <- r
	}
}

func (p *Pool[T, R]) Submit(job T) {
	p.jobs <- job
}

func (p *Pool[T, R]) Close() {
	close(p.jobs)
}

func (p *Pool[T, R]) Results() <-chan R {
	return p.results
}

func (p *Pool[T, R]) Err() <-chan error {
	return p.err
}
```

## Trade-offs

- **errgroup.SetLimit**: минимум кода, автоматическая отмена по первой ошибке; нет контроля над очередью.
- **Явный пул**: полный контроль (backpressure через буфер jobs, приоритеты), но больше кода и больше мест для ошибок (deadlock, утечки).
- Не закрывайте `jobs`, пока воркеры могут писать в `results` — deadlock.
- `go test -race` обязателен.

## Related

- [snippets/goroutines.md](../snippets/goroutines.md)
