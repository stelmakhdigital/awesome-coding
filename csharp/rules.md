---
id: csharp-rules
title: C# Rules
lang: csharp
min_version: "10"
category: rule-set
tags: [rules, guardrails, style, async, errors]
status: stable
updated: 2026-09-06
---

# C# Rules — обязательные guardrails

## Async

- ✅ `async/await` для асинхронных операций; метод `async`, если в нём есть `await`.
- ❌ `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` — deadlock в UI/WCF-контекстах, потеря threadpool-потока.
- ✅ `CancellationToken` — обязательный параметр долгих операций (network, БД, файлы).
- ✅ `await foreach` + `IAsyncEnumerable<T>` для асинхронных потоков.
- ✅ `async Task Main` — точка входа может быть async.
- ❌ `async void` — только в event handlers (и там — с try/catch на всё).

## Ошибки

- ✅ Исключения — для **исключительных** ситуаций; `catch` с фильтром (`when`), только то, что можно обработать.
- ❌ Исключения как поток управления (if/else → исключения).
- ✅ Кастомные исключения наследуются от конкретного базового (`InvalidOperationException`, не `Exception`).
- ✅ Перехват → лог + контекст → rethrow через `throw;` (сохраняет stack trace), не `throw ex;`.
- ✅ `ArgumentNullException.ThrowIfNull(arg)` / `ArgumentException.ThrowIfNegative` для валидации аргументов.

## Типы и null

- ✅ `<Nullable>enable</Nullable>`; `?` — осознанно, `!` — только с комментарием почему безопасно.
- ✅ `required` для обязательных полей в `record`/конструкторах.
- ✅ `sealed` по умолчанию; `abstract` — только при реальной иерархии.
- ✅ `record` для неизменяемых данных-переносчиков (DTO, конфигурации).
- ✅ Pattern matching: `is`, `switch`-выражения, property patterns — вместо ладдеров `if (x is T t)`.

## Ресурсы и DI

- ✅ `IDisposable` — через `using` (declaration: `using var x = ...`).
- ✅ Зависимости — через конструктор (primary constructor), не `new` внутри класса.
- ✅ Один класс — одна ответственность; god-классы распадаются.
- ❌ Статическое состояние (singletons «вручную») — DI-контейнер.

## Коллекции

- ✅ `List<T>`, `Dictionary<TKey,TValue>` — базовый набор; `Immutable*` при шаринге между потоками.
- ✅ Collection expressions: `var xs = [1, 2, 3];`
- ✅ `Span<T>`/`ReadOnlySpan<T>` для горячих путей (без аллокаций).
- ✅ LINQ — для читаемости; в горячих циклах — обычный `foreach` (проверьте бенчмарком).
- ✅ `Count` (O(1) для List), не `.Count()` (LINQ-расширение).

## Разное

- ✅ `const`/`static readonly`/enum вместо магических чисел и строк.
- ✅ XML doc для публичного API.
- ✅ `nameof()` в сообщениях об ошибках и логировании.
- ✅ `TimeProvider` вместо `DateTime.Now` (тестируемость времени).
- ❌ `Thread.Sleep` в async-коде — `await Task.Delay`.
- ❌ Строки через `+` в циклах — `StringBuilder`.

## Related

- [idioms.md](idioms.md) — идиомы с примерами
- [decisions.md](decisions.md) — выбор библиотек
