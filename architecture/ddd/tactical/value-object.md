---
id: ddd-value-object
title: DDD: Value Object
lang: shared
min_version: "1.21"
category: pattern
tags: [ddd, value-object, immutability, domain, go]
status: stable
updated: 2026-09-06
---

# Value Object (объект значения)

Объект определяется **значением**, а не идентичностью: два `Money{100, "USD"}` —
одинаковые объекты. Невозможно ответить «какой из них настоящий».

**Когда использовать** — неизменяемые описания: деньги, интервалы, email, адрес, цвет.
**Когда НЕ использовать** — объект с жизненным циклом и идентичностью → [entity](entity.md).

## Код (Go)

```go
package money

import (
	"errors"
	"fmt"
)

var (
	ErrNoCurrency       = errors.New("money: empty currency")
	ErrCurrencyMismatch = errors.New("money: currency mismatch")
)

// Value object: равенство по значению, иммутабельность.
// Передаётся по значению (копии независимы).
type Money struct {
	amount   int64 // в центах, НЕ float
	currency string
}

// Конструктор валидирует: невалидное значение невозможно создать.
func New(amount int64, currency string) (Money, error) {
	if currency == "" {
		return Money{}, ErrNoCurrency
	}
	return Money{amount: amount, currency: currency}, nil
}

// Операции возвращают НОВЫЕ значения — исходный не меняется.
func (m Money) Add(other Money) (Money, error) {
	if m.currency != other.currency {
		return Money{}, ErrCurrencyMismatch
	}
	return Money{amount: m.amount + other.amount, currency: m.currency}, nil
}

func (m Money) Sub(other Money) (Money, error) {
	if m.currency != other.currency {
		return Money{}, ErrCurrencyMismatch
	}
	return Money{amount: m.amount - other.amount, currency: m.currency}, nil
}

func (m Money) Less(other Money) bool {
	return m.amount < other.amount
}

func (m Money) String() string {
	return fmt.Sprintf("%d %s", m.amount, m.currency)
}
```

## Правила

- **Иммутабельность**: нет сеттеров; все операции возвращают новые значения.
- **Инварианты в конструкторе**: `Money` нельзя создать без валюты; `Email` — невалидным.
- **Равенство по всем полям** (в Go — `==` для структур из сравнимых полей).
- Безопасны для шаринга: копирование и передача по значению без сюрпризов.

## Антипаттерны

- ❌ `float` для денег — используйте целые единицы (центы).
- ❌ «Value object» с сеттерами — это уже не value object.
- ❌ Конструктор, допускающий невалидное состояние (Money с нулевой валютой, Email без `@`).
- ❌ Глубокие вложенные VO с указателями — теряется семантика значения.

## Related

- [entity.md](entity.md) — противоположность: идентичность
- [aggregate.md](aggregate.md) — VO часто живут внутри агрегатов
