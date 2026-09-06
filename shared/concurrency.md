---
id: shared-concurrency
title: "Shared: Concurrency (кросс-языковые принципы)"
lang: shared
min_version: null
category: concept
tags: [concurrency, parallelism, cancellation, principles]
status: stable
updated: 2026-09-06
---

# Concurrency — принципы

**Когда использовать** — любая параллельная/асинхронная работа.
**Когда НЕ использовать** — CPU-задачи без параллелизма (просто вызов).

## Принципы

1. **Ограничивайте параллелизм** (worker pool / semaphore): без лимита — DDoS себе.
2. **Канселяция — сквозная**: контекст/токен пробрасывается вниз по всей цепочке.
3. **Не блокируйте главный поток/тред**: IO — асинхронно, CPU — пул воркеров.
4. **Данные не шарятся мутабельно**: message passing (каналы/сообщения) предпочтительнее
   shared memory + locks; если locks — один владелец, короткий критсек.
5. **Идемпотентность на ретрай**: параллельные повторные вызовы не должны ломать состояние.
6. **Никакого busy-wait**: спите/ждите события, не крутите цикл с проверкой.

## ✅ / ❌

- ✅ `errgroup`/`WaitGroup` + лимит параллелизма
- ❌ «Запустил 1000 задач и жду» без пула
- ✅ Отмена: `context`/`CancellationToken`/`Job` — в каждом слое
- ❌ Заблокированный `await`/`.Result`/`join()` в UI-потоке
- ✅ Data race проверяется рэйс-детектором (Go: `-race`, TS: n/a, C#: analyzers)
- ❌ «У меня нет гонок, я проверил глазами»

## Идиомы по языкам

| Язык | Механизм | Детали |
|---|---|---|
| Go | goroutines + channels + context | [go/snippets/goroutines.md](../go/snippets/goroutines.md) |
| C# | `async/await` + `CancellationToken` | [csharp/snippets/async-await.md](../csharp/snippets/async-await.md) |
| Kotlin | корутины + `CoroutineScope` + `Flow` | [kotlin/snippets/coroutines.md](../kotlin/snippets/coroutines.md) |
| Python | `asyncio` + `TaskGroup` | [python/](../python/) |
| TS/JS | `Promise.all` + `AbortController` | [typescript/snippets/http-client.md](../typescript/snippets/http-client.md) |
| Unity | корутины + `async/await` | [unity/rules.md](../unity/rules.md) |

## Пример (Go)

```go
// Ограниченный параллелизм: N воркеров, отмена через context.
func FetchAll(ctx context.Context, urls []string, workers int) ([]Result, error) {
    jobs := make(chan string, len(urls))
    for _, u := range urls {
        jobs <- u
    }
    close(jobs)

    var (
        mu     sync.Mutex
        results []Result
        errs   []error
    )

    g, gctx := errgroup.WithContext(ctx)
    g.SetLimit(workers)
    for i := 0; i < workers; i++ {
        g.Go(func() error {
            for url := range jobs {
                r, err := fetch(gctx, url)
                mu.Lock()
                if err != nil {
                    errs = append(errs, err)
                } else {
                    results = append(results, r)
                }
                mu.Unlock()
            }
            return nil
        })
    }
    if err := g.Wait(); err != nil {
        return nil, fmt.Errorf("fetch all: %w", err)
    }
    return results, nil
}
```

## Related

- [error-handling.md](error-handling.md) — ошибки в параллельном коде
- [go/patterns/worker-pool.md](../go/patterns/worker-pool.md) — пул воркеров
