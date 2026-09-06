---
id: arch-cqrs
title: "Архитектура: CQRS"
lang: shared
min_version: "1.21"
category: pattern
tags: [architecture, cqrs, read-write, projections, advanced, go]
status: experimental
updated: 2026-09-06
---

# CQRS (Command Query Responsibility Segregation)

Разделение моделей **записи** (commands → агрегаты DDD) и **чтения**
(queries → денормализованные read-модели).

**Когда использовать** — нагрузка на чтение ≫ запись; модели чтения и записи реально
расходятся (отчёты, каталоги, дашборды); высокая конкуренция на запись.
**Когда НЕ использовать** — простой CRUD (одна модель на всё — нормальное решение);
«CQRS на всякий случай» — антипаттерн (см. [../decisions.md](../decisions.md)).

## Схема

```
Commands ──▶ Write side (агрегаты DDD, инварианты) ──▶ Events ──▶ Projections ──▶ Read models
Queries  ──▶ Read side (оптимизированные под запросы) ◀──────────┘
```

Чтение и запись — **eventually consistent**: после команды read-модель обновляется
с задержкой (обычно миллисекунды).

## Код (Go)

```go
// Write side: команда → агрегат.
package order

import "context"

// Упрощённые определения для примера (модель — в ddd/tactical/).
type OrderID string

type Item struct {
	SKU string
	Qty int
}

type Order struct {
	id OrderID
}

func (o *Order) ID() OrderID { return o.id }

func NewOrder(customer string, items []Item) (*Order, error) {
	return &Order{id: OrderID(customer)}, nil
}

type OrderRepository interface {
	Save(ctx context.Context, o *Order) error
}

type CreateOrderCommand struct {
	CustomerID string
	Items      []Item
}

type CommandHandler struct {
	repo OrderRepository
}

func (h *CommandHandler) CreateOrder(ctx context.Context, cmd CreateOrderCommand) (OrderID, error) {
	o, err := NewOrder(cmd.CustomerID, cmd.Items) // инварианты в модели
	if err != nil {
		return "", err
	}
	if err := h.repo.Save(ctx, o); err != nil {
		return "", err
	}
	return o.ID(), nil // события публикует application layer (outbox)
}
```

```go
// Read side: query → read-модель (отдельная схема БД).
package order

import (
	"context"
	"database/sql"
)

type OrderSummary struct {
	ID       string
	Customer string
	Total    int64
	Status   string
}

type QueryService struct {
	db *sql.DB // отдельная read-БД (или та же, но отдельные таблицы)
}

func (s *QueryService) ListByCustomer(ctx context.Context, customer string) ([]OrderSummary, error) {
	// SELECT из денормализованной таблицы orders_read.
	return nil, nil
}
```

```go
// Projection: событие → обновление read-модели.
package order

import (
	"context"
	"database/sql"
)

// Событие из write side (см. ddd/tactical/domain-event.md).
type OrderConfirmed struct {
	OrderID OrderID
}

type OrderProjection struct {
	readDB *sql.DB
}

func (p *OrderProjection) OnOrderConfirmed(ctx context.Context, e OrderConfirmed) error {
	_, err := p.readDB.ExecContext(ctx,
		`UPDATE orders_read SET status = 'confirmed' WHERE id = $1`, e.OrderID)
	return err
}
```

## Правила

1. **Разные схемы** для read и write (хотя бы разные таблицы): read-модель — денормализована под запросы.
2. **Read-модель — производная**: её нельзя менять напрямую, только через проекции событий.
3. **Учитывайте eventual consistency** в UX («обновите через секунду») и в тестах.
4. **Начинайте с одной модели**: разделяйте, когда появится конкретный запрос, который не тянет write-модель.

## Антипаттерны

- ❌ CQRS без event sourcing и без реальной асимметрии — сложность без пользы.
- ❌ Read-модель, которую «подправляют» прямо в БД (обход проекций).
- ❌ Две модели, которые должны быть strongly consistent «здесь и сейчас».

## Related

- [event-sourcing.md](event-sourcing.md) — события как хранилище
- [event-driven.md](event-driven.md) — доставка событий
- [../ddd/tactical/domain-event.md](../ddd/tactical/domain-event.md)
