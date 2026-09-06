---
id: csharp-async-await
title: Async/await: Task.WhenAll, CancellationToken
lang: csharp
min_version: "10"
category: snippet
tags: [async, await, task, cancellation, concurrency]
status: stable
updated: 2026-09-06
---

# Async/Await (C#)

**Когда использовать** — любая асинхронная работа: IO, HTTP, БД.
**Когда НЕ использовать** — CPU-задачи (async не ускоряет вычисления; для них — `Task.Run` осознанно).

## Код

```csharp
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

// async Main — точка входа может быть async.
var svc = new ReportService();
using var cts = new CancellationTokenSource(5_000);
var reports = await svc.GetAllAsync(cts.Token);
Console.WriteLine($"Got {reports.Count} reports");

public sealed class ReportService
{
    // CancellationToken — обязательный параметр долгих операций.
    public async Task<List<Report>> GetAllAsync(CancellationToken ct)
    {
        // Параллельно: WhenAll — все должны завершиться.
        var tasks = new[]
        {
            FetchAsync("a", ct),
            FetchAsync("b", ct),
            FetchAsync("c", ct),
        };
        var results = await Task.WhenAll(tasks);
        return [.. results]; // collection expression (C# 12)
    }

    public static async Task<Report> FetchAsync(string id, CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();
        await Task.Delay(10, ct); // имитация IO; ❌ Thread.Sleep
        return new Report(id);
    }
}

public sealed record Report(string Id);
```

## Правила

- ✅ `async/await` — метод `async`, если в нём есть `await` (иначе — возвращайте `Task.FromResult`).
- ❌ `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` — deadlock в UI-контекстах.
- ✅ `CancellationToken` — пробрасывайте вниз по цепочке; `cts.Token` из `CancellationTokenSource`.
- ✅ `await foreach` + `IAsyncEnumerable<T>` — асинхронные потоки.
- ✅ `Task.WhenAll` (все) / `Task.WhenAny` (первый) — явный выбор параллелизма.
- ❌ `async void` — только event handlers (и там — try/catch на всё).
- ✅ Таймауты: `CancellationTokenSource(TimeSpan)` или `LinkToSource`.

## Related

- [rules.md — async](../rules.md)
- [decisions.md — HTTP-клиент](../decisions.md)
