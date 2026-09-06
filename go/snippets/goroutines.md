---
id: go-goroutines
title: Goroutines: WaitGroup, errgroup, worker pool
lang: go
min_version: "1.20"
category: snippet
tags: [concurrency, goroutines, workers, errgroup]
status: stable
updated: 2026-09-06
---

# Goroutines

**Когда использовать** — параллельное выполнение задач, ограничение параллелизма, fan-in/fan-out.
**Когда НЕ использовать** — когда задача тривиально последовательная: не усложняйте.

## Код

```go
package worker

import (
	"context"
	"fmt"
	"sync"

	"golang.org/x/sync/errgroup"
)

// 1. WaitGroup — ожидание набора goroutine.
func RunAll(tasks ...func()) {
	var wg sync.WaitGroup
	for _, t := range tasks {
		wg.Add(1)
		go func() {
			defer wg.Done()
			t()
		}()
	}
	wg.Wait()
}

// 2. errgroup — первый error + автоматическая отмена остальных через ctx.
func RunAllWithErr(ctx context.Context, tasks ...func(context.Context) error) error {
	g, gctx := errgroup.WithContext(ctx)
	for _, t := range tasks {
		g.Go(func() error { return t(gctx) })
	}
	return g.Wait() // nil или первая ошибка
}

// 3. Ограничение параллелизма: errgroup.SetLimit (1.20+).
func MapParallel[T, R any](ctx context.Context, workers int, items []T,
	f func(context.Context, T) (R, error),
) ([]R, error) {
	g, gctx := errgroup.WithContext(ctx)
	g.SetLimit(workers)
	results := make([]R, len(items))
	for i, item := range items {
		i, item := i, item // явная копия (в 1.22+ loopvar — на итерацию, но явность не вредит)
		g.Go(func() error {
			v, err := f(gctx, item)
			if err != nil {
				return fmt.Errorf("item %d: %w", i, err)
			}
			results[i] = v // разные индексы — race-free
			return nil
		})
	}
	if err := g.Wait(); err != nil {
		return nil, err
	}
	return results, nil
}

// 4. Worker pool с каналами (классика).
func WorkerPool[T, R any](ctx context.Context, workers int,
	jobs <-chan T, f func(T) R,
) <-chan R {
	results := make(chan R)
	var wg sync.WaitGroup
	for i := 0; i < workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := range jobs { // завершается, когда jobs закрыт
				select {
				case <-ctx.Done():
					return
				case results <- f(j):
				}
			}
		}()
	}
	go func() {
		wg.Wait()
		close(results)
	}()
	return results
}
```

## Pitfalls

- Loop variable до 1.22: захват переменной цикла по ссылке — копируйте (`i, item := i, item`).
- Goroutine без пути завершения — утечка; всегда ctx/канал/WaitGroup.
- Не закрывайте канал, в который пишут другие (panic: send on closed channel).
- Канал без буфера + приёмник, который не читает — deadlock.
- `go test -race` — обязательно для конкурентного кода.

## Alternatives

- `golang.org/x/sync/semaphore` — ручной лимит параллелизма без errgroup.
- `golang.org/x/sync/singleflight` — дедупликация одновременных запросов.

## Related

- [patterns/worker-pool.md](../patterns/worker-pool.md)
- [context.md](context.md)
