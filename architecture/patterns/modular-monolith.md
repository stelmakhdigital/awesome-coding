---
id: arch-modular-monolith
title: "Архитектура: Modular Monolith"
lang: shared
min_version: "1.21"
category: pattern
tags: [architecture, modular-monolith, modules, boundaries, go]
status: stable
updated: 2026-09-06
---

# Modular Monolith (модульный монолит)

Один deployable, но с **жёсткими модульными границами**: каждый модуль —
свой API, свои данные, своя внутренняя реализация.

**Когда использовать** — несколько команд/доменов в одном репозитории;
подготовка к будущему разделению на микросервисы; «маленькие микросервисы
без сетевых вызовов».
**Когда НЕ использовать** — маленький сервис (модули = оверхед);
необходимо независимое масштабирование частей → [microservices](microservices.md).

## Код (Go) — структура

```
internal/
├── ordering/
│   ├── api/        # публичный API модуля (единственная точка входа для соседей)
│   └── internal/   # приватная реализация (модель, репозитории)
├── billing/
│   ├── api/
│   └── internal/
└── platform/       # инфраструктурные общие сервисы (auth, logging)
    ├── auth/api/
    └── ...
```

```go
// ordering/api: всё, что другие модули МОГУТ использовать.
package api

import "context"

type OrderConfirmed struct {
	OrderID    string
	TotalCents int64
	Currency   string
}

type Service interface {
	Confirm(ctx context.Context, orderID string) error
	// События для других модулей — через event bus, не через прямой вызов.
}
```

```go
// billing/internal: использует ordering ТОЛЬКО через ordering/api.
package internal

import (
	"context"

	ordering "example.com/shop/internal/ordering/api"
)

type BillingService struct {
	orders ordering.Service
}

// Межмодульный вызов — только через API модуля.
func (s *BillingService) ChargeForOrder(ctx context.Context, orderID string) error {
	return s.orders.Confirm(ctx, orderID)
}
```

## Правила

1. **Сосед видит только `api/`**: импорты `internal/<mod>/internal` из других модулей — нарушение.
2. **Каждый модуль владеет своими таблицами**: чужие таблицы не читаются напрямую.
3. **Межмодульное взаимодействие**: через `api` (синхронно) или события (асинхронно) — не через общие структуры данных.
4. **Принудительные границы**: linter зависимостей (go-arch-lint, archguard) в CI.
5. **Общий код — только в `platform/`** и только инфраструктурный (auth, логирование).

## Проверка границ (CI)

```yaml
# go-arch-lint: запрет импортов internal чужих модулей
# (пример конфигурации — см. документацию go-arch-lint)
```

## Антипаттерны

- ❌ «Shared»-модуль, в который выносят всё (мусорка → границы исчезают).
- ❌ Модули, которые читают таблицы соседа «временно».
- ❌ Границы «на словах»: без линтера они размоются за месяцы.

## Related

- [microservices.md](microservices.md) — когда монолита мало
- [../ddd/strategic/bounded-context.md](../ddd/strategic/bounded-context.md) — модуль ≈ bounded context
- [go/rules.md](../../go/rules.md)
