---
id: ddd-domain-event
title: DDD: Domain Event
lang: shared
min_version: "1.21"
category: pattern
tags: [ddd, domain-event, events, go]
status: stable
updated: 2026-09-06
---

# Domain Event (доменное событие)

Факт, который **уже произошёл** в домене: `OrderConfirmed`, `PaymentReceived`.
События связывают части домена без прямой зависимости.

**Когда использовать** — реакция на факт домена (оплата → отгрузка; подтверждение → биллинг),
особенно когда обработчик живёт в другом модуле/контексте.
**Когда НЕ использовать** — простая синхронная последовательность внутри одного use case
(просто вызовите метод); «событие» как замена вызову функции внутри одного модуля.

## Код (Go)

```go
package order

import (
	"errors"
	"time"
)

// Минимальные определения для примера (полная модель — в entity.md).
var ErrInvalidTransition = errors.New("order: invalid transition")

type OrderID string

type OrderStatus string

const (
	StatusNew       OrderStatus = "new"
	StatusConfirmed OrderStatus = "confirmed"
)

// Domain event: факт в прошедшем времени.
type OrderConfirmed struct {
	OrderID     OrderID
	ConfirmedAt time.Time
}

type PaymentReceived struct {
	OrderID OrderID
	Amount  int64 // в центах
}

// Общий маркер для событий домена.
type DomainEvent interface{ event() }

func (OrderConfirmed) event() {
}

func (PaymentReceived) event() {
}

// Агрегат ЗАПИСЫВАЕТ события; публикует их слой выше (application).
type Order struct {
	id     OrderID
	status OrderStatus
	events []DomainEvent
}

func (o *Order) Confirm() error {
	if o.status != StatusNew {
		return ErrInvalidTransition
	}
	o.status = StatusConfirmed
	o.events = append(o.events, OrderConfirmed{OrderID: o.id, ConfirmedAt: time.Now()})
	return nil
}

// PullEvents: application layer забирает события после сохранения.
func (o *Order) PullEvents() []DomainEvent {
	events := o.events
	o.events = nil
	return events
}
```

## Правила

1. **Прошедшее время**: `OrderConfirmed`, не `ConfirmOrder` (это команда).
2. **Событие — факт, а не запрос**: обработчик не «обязан» что-то делать; он реагирует.
3. **Домен не публикует**: агрегат накапливает события, публикует application layer
   (домен не знает о шине/БД/HTTP).
4. **Неизменяемость**: поля события не меняются после создания.
5. **Версионируйте схему** (поле `Version` или отдельные типы) — события живут дольше кода.

## Антипаттерны

- ❌ Событие как команда: `SendEmail` — это команда, а не факт домена.
- ❌ Публикация из домена (инъекция шины в агрегат) — домен начинает зависеть от инфраструктуры.
- ❌ «Событие» с мутабельными полями, которые обработчики дописывают.
- ❌ Событие на каждый геттер — шум вместо фактов.

## Related

- [event-driven.md](../../patterns/event-driven.md) — доставка событий (outbox, шины)
- [event-sourcing.md](../../patterns/event-sourcing.md) — события как хранилище состояния
- [cqrs.md](../../patterns/cqrs.md) — события для построения read-моделей
