---
id: csharp-logging
title: Logging: Microsoft.Extensions.Logging, scopes
lang: csharp
min_version: "10"
category: snippet
tags: [logging, structured, scopes, mext]
status: stable
updated: 2026-09-06
---

# Logging (C#)

**Когда использовать** — `ILogger<T>` (Microsoft.Extensions.Logging): структурированные
сообщения, scopes, уровни.
**Когда НЕ использовать** — `Console.WriteLine` в production-коде; `Debug.WriteLine`.

## Код

```csharp
using Microsoft.Extensions.Logging;

// ILogger<T> — через DI (primary constructor).
public sealed class OrderService(ILogger<OrderService> logger)
{
    public void Confirm(string orderId, decimal total)
    {
        // Scope: контекст операции попадёт в каждый запис внутри.
        using (logger.BeginScope("Order {OrderId}", orderId))
        {
            // Структурированные сообщения: плейсхолдеры {Name}, не string-конкатенация.
            logger.LogInformation("Confirming order {OrderId}, total {Total:C}", orderId, total);
            try
            {
                DoWork(orderId);
            }
            catch (Exception ex)
            {
                // Exception — последний аргумент; пишется со stack trace.
                logger.LogError(ex, "Failed to confirm order {OrderId}", orderId);
                throw;
            }
        }
    }

    private void DoWork(string orderId)
    {
    }
}
```

## Правила

- ✅ Структурированные сообщения: `log.LogInformation("x {X}", x)` — НЕ `$"x {x}"`.
- ✅ Уровни: `Trace/Debug` — диагностика, `Information` — жизненный цикл, `Warning` — аномалия с обработкой, `Error` — сбой.
- ✅ Exception — всегда последним аргументом (`LogError(ex, "...")`).
- ✅ Scopes — для запросов/операций (ASP.NET Core создаёт scope на запрос автоматически).
- ❌ Логирование секретов (токены, пароли, PII) — маскируйте.
- ✅ `IsLogEnabled(LogLevel.X)` — перед дорогим формированием сообщения.

## Related

- [decisions.md — логирование](../decisions.md)
- [error-handling.md](error-handling.md)
