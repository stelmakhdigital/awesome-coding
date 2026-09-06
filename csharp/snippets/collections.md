---
id: csharp-collections
title: "Collections: List, Dictionary, Span, LINQ"
lang: csharp
min_version: "10"
category: snippet
tags: [collections, linq, span, immutable]
status: stable
updated: 2026-09-06
---

# Collections (C#)

**Когда использовать** — работа с коллекциями: выбор структуры, LINQ vs циклы, Span.
**Когда НЕ использовать** — горячий путь с аллокациями: `Span<T>`/`ReadOnlySpan<T>` вместо LINQ.

## Код

```csharp
using System.Collections;
using System.Collections.Generic;
using System.Linq;

// Базовые коллекции.
var list = new List<string> { "a", "b" };
var dict = new Dictionary<string, int> { ["a"] = 1 };

// Collection expressions (C# 12): нужен тип-приёмник (var не подойдёт).
int[] xs = [1, 2, 3];
var ys = new List<int>(xs);

// Count — O(1) для List; не LINQ-расширение .Count().
Console.WriteLine(list.Count);

// LINQ — для читаемости цепочек.
var upper = list.Select(s => s.ToUpperInvariant()).ToList();
var evens = xs.Where(x => x % 2 == 0).ToArray();

// В горячих циклах — обычный foreach (проверьте бенчмарком).
var sum = 0;
foreach (var x in xs)
{
    sum += x;
}

// Immutable-коллекции при шаринге между потоками.
var immutable = System.Collections.Immutable.ImmutableArray.Create(1, 2, 3);
_ = immutable[0];

// Span — без аллокаций (стек/пиннинг), только для горячих путей.
static int Sum(ReadOnlySpan<int> values)
{
    var total = 0;
    for (var i = 0; i < values.Length; i++)
    {
        total += values[i];
    }
    return total;
}

Console.WriteLine(Sum(xs.AsSpan()));
```

## Выбор структуры

| Задача | Структура |
|---|---|
| Список, доступ по индексу | `List<T>` |
| Поиск по ключу | `Dictionary<TKey,TValue>` |
| Уникальные значения | `HashSet<T>` |
| FIFO | `Queue<T>` |
| LIFO | `Stack<T>` |
| Неизменяемое | `ImmutableArray<T>`, `IReadOnlyList<T>` |
| Горячий путь, без аллокаций | `Span<T>` |

## Pitfalls

- ❌ `List<T>` при шаринге между потоками без синхронизации.
- ❌ LINQ в горячих циклах без бенчмарка.
- ❌ `Span<T>` как поле класса/в `async`-метод (stack-семантика) — только локально.
- ✅ `IReadOnlyList<T>`/`IReadOnlyDictionary` в сигнатурах — не обещаете мутацию.

## Related

- [rules.md — коллекции](../rules.md)
