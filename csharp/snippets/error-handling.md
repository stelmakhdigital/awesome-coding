---
id: csharp-error-handling
title: "Error handling: исключения, фильтры, валидация аргументов"
lang: csharp
min_version: "10"
category: snippet
tags: [errors, exceptions, validation, retry]
status: stable
updated: 2026-09-06
---

# Error handling (C#)

**Когда использовать** — любая обработка ошибок: кастомные исключения, retry, валидация.
**Когда НЕ использовать** — исключения как поток управления (if/else → исключения).

## Код

```csharp
// Кастомное исключение — от конкретного базового, не от Exception.
public sealed class OrderNotFoundException(string orderId)
    : InvalidOperationException($"Order {orderId} not found");

// Валидация аргументов — встроенные helpers (.NET 6+).
public static class Validation
{
    public static void Confirm(string? id)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(id);
    }
}

// Фильтры catch: ловим только то, что можем обработать.
public static class Retry
{
    public static T WithRetry<T>(Func<T> action, int attempts = 3)
    {
        for (var i = 1; ; i++)
        {
            try
            {
                return action();
            }
            catch (IOException) when (i < attempts)
            {
                // временная ошибка — повторяем
            }
            catch (FileNotFoundException)
            {
                // не восстановимся — пробрасываем (throw; сохраняет stack trace)
                throw;
            }
        }
    }
}

// Rethrow: `throw;` — да, `throw ex;` — нет (обрезает stack trace).
public static class Pipeline
{
    public static void Run()
    {
        try
        {
            throw new OrderNotFoundException("42");
        }
        catch (OrderNotFoundException)
        {
            // логирование с контекстом (см. snippets/logging.md)
            throw;
        }
    }
}
```

## Pitfalls

- ❌ `catch (Exception)` «на всякий случай» — скрывает баги; ловите конкретные типы.
- ❌ Пустой `catch {}` — минимум `throw;` или осознанный лог.
- ❌ `throw ex;` — теряется исходный stack trace; только `throw;`.
- ❌ Исключения для ожидаемых ситуаций (не найден, невалидный ввод) — возвращайте `null`/`bool`/Result.
- ✅ `when`-фильтры — условие прямо в `catch`.

## Related

- [rules.md — ошибки](../rules.md)
- [logging.md](logging.md) — логирование ошибок
