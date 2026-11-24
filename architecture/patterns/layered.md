---
id: arch-layered
title: "Архитектура: Layered (слоистая)"
lang: shared
min_version: "1.21"
category: pattern
tags: [architecture, layered, handlers, services, go]
status: stable
updated: 2026-11-24
---

# Layered Architecture (слоистая)

Классика: запрос проходит слои, каждый знает только о следующем.

```
HTTP/gRPC handlers → application (use cases, транзакции) → domain (модель, инварианты) → infrastructure (БД, мессенджеры)
```

**Когда использовать** — большинство сервисов; уровень DDD 0–1. Самый простой
вариант, который сохраняет границы.
**Когда НЕ использовать** — несколько интерфейсов (HTTP + CLI + gRPC) с одной логикой
→ [hexagonal](hexagonal.md); сложное доменное поведение → DDD + hexagonal.

## Код (Go)

```
internal/
├── api/          # handlers: парсинг, валидация формата, маппинг ошибок
├── application/  # use cases: оркестрация, транзакции
├── domain/       # модель и правила (без зависимостей наружу)
└── infra/        # БД, мессенджеры, внешние API
```

```go
// api: тонкий handler — НИКАКОЙ бизнес-логики.
package api

import (
	"context"
	"net/http"
)

// OrderService — контракт application-слоя (реализация ниже).
type OrderService interface {
	Confirm(ctx context.Context, id string) error
}

type OrderHandler struct {
	orders OrderService
}

func (h *OrderHandler) Confirm(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if err := h.orders.Confirm(r.Context(), id); err != nil {
		writeError(w, err) // маппинг доменных ошибок на HTTP-статусы
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func writeError(w http.ResponseWriter, err error) {
	http.Error(w, err.Error(), http.StatusInternalServerError)
}
```

```go
// domain: модель, инварианты и контракт хранилища (не знает про HTTP и БД).
package domain

import (
	"context"
	"errors"
)

var ErrAlreadyConfirmed = errors.New("order already confirmed")

type Event struct{ OrderID string }

type Order struct {
	id        string
	confirmed bool
	events    []Event
}

// Confirm — инвариант здесь, не в handler'е и не в infra.
func (o *Order) Confirm() error {
	if o.confirmed {
		return ErrAlreadyConfirmed
	}
	o.confirmed = true
	o.events = append(o.events, Event{OrderID: o.id})
	return nil
}

func (o *Order) PullEvents() []Event {
	ev := o.events
	o.events = nil
	return ev
}

// Tx — единица транзакции хранилища; реализация — в другом слое.
type Tx interface {
	Get(ctx context.Context, id string) (*Order, error)
	Save(ctx context.Context, o *Order) error
	Commit(ctx context.Context) error
}

type OrderRepository interface {
	Begin(ctx context.Context) (Tx, error)
}
```

```go
// application: use case — оркестрация и транзакции.
package application

import (
	"context"

	"example.com/layered/domain"
)

type OrderService struct {
	repo   domain.OrderRepository
	events Events
}

// Events — порт публикации: реализацию подставляет infra.
type Events interface {
	Publish(ctx context.Context, events ...domain.Event) error
}

func (s *OrderService) Confirm(ctx context.Context, id string) error {
	tx, err := s.repo.Begin(ctx)
	if err != nil {
		return err
	}
	order, err := tx.Get(ctx, id)
	if err != nil {
		return err
	}
	if err := order.Confirm(); err != nil { // инвариант — в модели
		return err
	}
	if err := tx.Save(ctx, order); err != nil {
		return err
	}
	if err := tx.Commit(ctx); err != nil {
		return err
	}
	return s.events.Publish(ctx, order.PullEvents()...)
}
```

## Правила

1. **Зависимости направлены вниз** (или через интерфейсы: domain не импортирует infra).
2. **Handler тонкий**: парсинг, аутентификация, маппинг ошибок — и всё.
3. **Бизнес-правила не в handlers и не в infra**: в domain/application.
4. **Транзакции — в application**, не в handlers.

## Антипаттерны

- ❌ «Толстый» handler: бизнес-логика в HTTP-коде.
- ❌ Domain импортирует драйвер БД «для удобства».
- ❌ Слой-«прокладка», который ничего не делает (лишняя абстракция).

## Related

- [hexagonal.md](hexagonal.md) — когда слоистой мало
- [../ddd/README.md](../ddd/README.md) — уровень DDD для слоёв
- [go/rules.md](../../go/rules.md) — правила Go-кода
