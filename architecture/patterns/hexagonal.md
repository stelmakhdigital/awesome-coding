---
id: arch-hexagonal
title: "Архитектура: Hexagonal (Ports & Adapters)"
lang: shared
min_version: "1.21"
category: pattern
tags: [architecture, hexagonal, ports-adapters, clean, go]
status: stable
updated: 2026-09-06
---

# Hexagonal Architecture (Ports & Adapters)

Ядро (domain + application) окружено **портами** (интерфейсами) и **адаптерами**
(реализации). Ядро не знает, что оно вызывается из HTTP и хранится в Postgres.

```
            ┌────────────────────────────────┐
            │          Application           │
            │   ┌────────────────────────┐   │
            │   │       Domain core      │   │
            │   └────────────────────────┘   │
            │   in-ports (use cases)         │
            │   out-ports (инфраструктура)   │
            └──────┬──────────────────┬──────┘
                   │                  │
          ┌────────▼────────┐  ┌──────▼─────────┐
          │ HTTP/gRPC/CLI   │  │  SQL / MQ /    │
          │ (in-adapters)   │  │  внешние API   │
          └─────────────────┘  │ (out-adapters) │
                               └────────────────┘
```

**Когда использовать** — несколько интерфейсов над одной логикой (HTTP + CLI + gRPC),
тестируемость без инфраструктуры, смена БД/мессенджера.
**Когда НЕ использовать** — простой CRUD-сервис с одним интерфейсом: [layered](layered.md)
достаточно.

## Код (Go)

```go
// out-port: ядро описывает, ЧТО ему нужно (не КАК).
package core

import "context"

type OrderID string

// Order — агрегат (полная модель — в ddd/tactical/aggregate.md).
type Order struct {
	id OrderID
}

func (o *Order) ID() OrderID { return o.id }

// Инвариант — в модели (см. ddd/tactical/aggregate.md).
func (o *Order) Confirm() error { return nil }

type OrderStore interface {
	Get(ctx context.Context, id OrderID) (*Order, error)
	Save(ctx context.Context, o *Order) error
}
```

```go
// use case (in-port): контракт для любого адаптера.
package core

import "context"

type ConfirmOrderUseCase interface {
	Confirm(ctx context.Context, id OrderID) error
}

type confirmOrder struct {
	store OrderStore
}

func NewConfirmOrder(store OrderStore) ConfirmOrderUseCase {
	return &confirmOrder{store: store}
}

func (uc *confirmOrder) Confirm(ctx context.Context, id OrderID) error {
	o, err := uc.store.Get(ctx, id)
	if err != nil {
		return err
	}
	return o.Confirm() // инвариант — в модели
}
```

```go
// in-adapter: HTTP реализует use case.
package api

import (
	"net/http"

	"example.com/shop/core"
)

type Handler struct {
	confirm core.ConfirmOrderUseCase
}

func (h *Handler) Confirm(w http.ResponseWriter, r *http.Request) {
	if err := h.confirm.Confirm(r.Context(), core.OrderID(r.PathValue("id"))); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
```

```go
// out-adapter: SQL реализует OrderStore.
package infra

import (
	"context"
	"database/sql"

	"example.com/shop/core"
)

type sqlOrderStore struct{ db *sql.DB }

func (s *sqlOrderStore) Get(ctx context.Context, id core.OrderID) (*core.Order, error) {
	// SELECT + восстановление доменной модели.
	return nil, nil
}
```

## Правила

1. **Ядро не импортирует адаптеры**: только интерфейсы (порты).
2. **Адаптеры — тонкие**: переводят формат (HTTP ↔ use case, SQL ↔ модель).
3. **DI на границе**: адаптеры собираются в `main`/композиционном корне.
4. **Тесты ядра — без инфраструктуры**: фейки портов.

## Антипаттерны

- ❌ «Hexagonal», где domain импортирует `database/sql` и `net/http`.
- ❌ Адаптер с бизнес-логикой (логика «переводит» в порту).
- ❌ Порт на каждый метод (интерфейс-«мусорка» с 20 методами) — порты должны быть по use case.

## Related

- [layered.md](layered.md) — более простой вариант
- [../ddd/tactical/repository.md](../ddd/tactical/repository.md) — repository как out-port
- [go/patterns/functional-options.md](../../go/patterns/functional-options.md) — конфигурация адаптеров
