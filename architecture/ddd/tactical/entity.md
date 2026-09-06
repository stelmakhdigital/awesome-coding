---
id: ddd-entity
title: DDD: Entity
lang: shared
min_version: "1.21"
category: pattern
tags: [ddd, entity, identity, domain, go]
status: stable
updated: 2026-09-06
---

# Entity (сущность)

Сущность определяется **идентичностью**, а не состоянием: две сущности с одинаковым
ID — одна и та же сущность, даже если их состояние изменилось.

**Когда использовать** — объект с жизненным циклом и изменяемым состоянием,
которое должно удовлетворять инвариантам домена.
**Когда НЕ использовать** — неизменяемые данные (деньги, адрес, email) → [value object](value-object.md).

## Код (Go)

```go
package order

import "errors"

var ErrEmptyOrder = errors.New("order: empty order")

type OrderID string

type OrderStatus string

const (
	StatusNew       OrderStatus = "new"
	StatusConfirmed OrderStatus = "confirmed"
)

// Entity: идентичность первична, состояние вторично.
// ID неизменяем; состояние меняется только через методы (инварианты).
type Order struct {
	id     OrderID
	status OrderStatus
	items  []OrderItem
}

type OrderItem struct {
	SKU      string
	Quantity int
}

// Конструктор валидирует начальное состояние.
func NewOrder(id OrderID, items []OrderItem) (*Order, error) {
	if len(items) == 0 {
		return nil, ErrEmptyOrder
	}
	return &Order{id: id, status: StatusNew, items: items}, nil
}

func (o *Order) ID() OrderID {
	return o.id
}

func (o *Order) Status() OrderStatus {
	return o.status
}

// Поведение: переходы состояния защищены инвариантами.
func (o *Order) Confirm() error {
	if o.status != StatusNew {
		return errors.New("order: cannot confirm, status is " + string(o.status))
	}
	o.status = StatusConfirmed
	return nil
}
```

## Правила

- **ID стабилен** и задаётся при создании (или генерируется); никогда не меняется.
- **Поля неэкспортированы**: состояние меняется только через методы — иначе инварианты ломаются извне.
- **Конструктор валидирует**: сущность нельзя создать в невалидном состоянии.
- Равенство — по ID, а не по полям.

## Антипаттерны

- ❌ Экспортированные поля (`type Order struct { ID string; Status string }`) — любой код может поставить `Status = "whatever"`.
- ❌ Anemic entity: только геттеры/сеттеры, вся логика в сервисах.
- ❌ Сравнение сущностей по содержимому (`reflect.DeepEqual`) — только по ID.

## Related

- [value-object.md](value-object.md) — когда объект НЕ сущность
- [aggregate.md](aggregate.md) — сущность внутри границы согласованности
- [../README.md — золотые правила DDD](../README.md)
