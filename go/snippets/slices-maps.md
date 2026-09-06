---
id: go-slices-maps
title: Slices и Maps (stdlib, Go 1.21+)
lang: go
min_version: "1.21"
category: snippet
tags: [slices, maps, stdlib, collections]
status: stable
updated: 2026-09-06
---

# Slices и Maps

**Когда использовать** — операции над срезами и мапами вместо ручных циклов.
**Когда НЕ использовать** — когда нужна сложная трансформация: рассмотрите `slices.Collect` (1.23+) или явный цикл.

## Код

```go
package collections

import (
	"cmp"
	"iter"
	"maps"
	"slices"
)

// --- Slices ---
func SliceOps(s []int) {
	_ = slices.Contains(s, 42) // есть ли элемент
	_ = slices.Index(s, 42)    // индекс или -1
	_ = slices.IndexFunc(s, func(x int) bool { return x > 10 })

	sorted := slices.Clone(s) // копия
	slices.Sort(sorted)       // сортировка in-place

	// SortFunc с cmp (1.21+).
	type P struct{ Name string }
	ps := []P{{"b"}, {"a"}}
	slices.SortFunc(ps, func(a, b P) int { return cmp.Compare(a.Name, b.Name) })

	_ = slices.Compact(s)      // убрать СОСЕДНИЕ дубликаты (сначала отсортируйте)
	_ = slices.Delete(s, 1, 3) // удалить диапазон [1,3)
	_ = append(s, 99)          // добавить: встроенный append (slices.Append не существует)

	// Min/Max для срезов: slices.Min/Max (1.21+).
	_ = slices.Min(s)
	_ = slices.Max(s)
}

// --- Maps ---
func MapOps(m map[string]int) {
	clear(m) // builtin (1.21+): очистить мапу

	// Итерация (1.23+): maps.Keys / maps.Values возвращают iter.Seq.
	for k := range maps.Keys(m) {
		_ = k
	}
	for v := range maps.Values(m) {
		_ = v
	}

	// Collect из итератора (1.23+).
	_ = slices.Collect(maps.Keys(m)) // []string
}

// --- Iter (1.23+) ---
func Filter[T any](seq iter.Seq[T], pred func(T) bool) iter.Seq[T] {
	return func(yield func(T) bool) {
		seq(func(v T) bool {
			if pred(v) {
				return yield(v)
			}
			return true
		})
	}
}
```

## Pitfalls

- `slices.Sort` требует, чтобы тип реализовывал `cmp.Ordered` (числа, строки, bool).
- `slices.Compact` убирает только **соседние** дубликаты — сначала `slices.Sort`.
- Итерация по мапе — в случайном порядке; не полагайтесь на порядок.
- `slices.Delete` не уменьшает capacity; для освобождения памяти — `slices.Clone` или новый срез.
- Builtins `min`/`max` (1.21+) не принимают форму `...` для срезов — для срезов используйте `slices.Min`/`slices.Max`.

## Related

- [idioms.md](../idioms.md)
