---
id: arch-microservices
title: "Архитектура: Microservices"
lang: shared
min_version: "1.21"
category: pattern
tags: [architecture, microservices, distributed, saga, go]
status: stable
updated: 2026-09-06
---

# Microservices (микросервисы)

Каждый сервис — отдельный deployable с собственной БД, владельцем и API.
Сервис ≈ [bounded context](../ddd/strategic/bounded-context.md).

**Когда использовать** — независимое масштабирование частей, независимые деплои,
разные команды/ownership, разные требования к надёжности/языкам.
**Когда НЕ использовать** — старт без выделенных доменных границ; «потому что модно»;
одна команда и один домен → [modular monolith](modular-monolith.md).

## Ценой чего (принять ВСЁ)

- сетевые вызовы вместо вызовов функций (латентность, отказы, таймауты);
- распределённые транзакции (saga, а не ACID);
- дублирование данных между сервисами;
- сложность наблюдаемости (tracing, корреляция логов);
- сложность деплоя (оркестрация, миграции, откаты).

## Правила

1. **Один сервис = один bounded context**; сервис владеет своими данными.
2. **Проектируйте на отказ**: таймауты, ретраи с backoff, идемпотентность, circuit breaker.
3. **Идемпотентность на входе**: повторный вызов не создаёт дублей (идемпотентные ключи).
4. **Коммуникация**: синхронно — API (редко, только когда нужен ответ); асинхронно — события.
5. **Никаких распределённых транзакций «как в монолите»**: saga (compensating actions).

## Код (Go) — идемпотентный обработчик

```go
package api

import "context"

// Упрощённые определения для примера.
type CreateOrder struct {
	Customer string
}

type Response struct {
	OrderID string
}

type OrderService interface {
	Create(ctx context.Context, cmd CreateOrder) (Response, error)
}

// Идемпотентность: повторный запрос с тем же ключом не дублирует действие.
type CreateOrderHandler struct {
	store  IdempotencyStore
	orders OrderService
}

type IdempotencyStore interface {
	// Возвращает сохранённый ответ, если ключ уже обработан.
	Begin(ctx context.Context, key string) (existing Response, ok bool, err error)
	Finish(ctx context.Context, key string, resp Response) error
}

func (h *CreateOrderHandler) Handle(ctx context.Context, key string, cmd CreateOrder) (Response, error) {
	if resp, ok, err := h.store.Begin(ctx, key); err != nil {
		return Response{}, err
	} else if ok {
		return resp, nil // повтор — возвращаем сохранённый ответ
	}
	resp, err := h.orders.Create(ctx, cmd)
	if err != nil {
		return Response{}, err
	}
	if err := h.store.Finish(ctx, key, resp); err != nil {
		return Response{}, err
	}
	return resp, nil
}
```

## Антипаттерны

- ❌ **Distributed monolith**: синхронные вызовы между каждым запросом, общая БД,
  деплой только «всем вместе».
- ❌ Микросервис на каждую сущность («CustomerService», «OrderService», «EmailService»…).
- ❌ Общая БД между сервисами.
- ❌ Ретраи без идемпотентности — дубли действий.

## Related

- [modular-monolith.md](modular-monolith.md) — ступенька сюда
- [event-driven.md](event-driven.md) — асинхронная интеграция
- [../ddd/strategic/bounded-context.md](../ddd/strategic/bounded-context.md)
