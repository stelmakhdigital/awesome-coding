---
id: ddd-bounded-context
title: "DDD: Bounded Context"
lang: shared
min_version: "n/a"
category: concept
tags: [ddd, bounded-context, strategic, boundaries, modules]
status: stable
updated: 2026-09-06
---

# Bounded Context (ограниченный контекст)

Граница, внутри которой действует **одна модель и один язык**. То же слово
разные значения в разных контекстах: «Order» для клиента — заявка, для склада —
набор строк отгрузки, для биллинга — основание для счёта.

**Когда использовать** — уровень DDD ≥ 2: несколько доменов/команд, у одного понятия
разные значения в разных частях системы.
**Когда НЕ использовать** — одна команда, одна модель: граница = весь сервис (уровень 0–1).

## Код (Go) — структура пакетов

```
internal/
├── ordering/            # Bounded context «Ordering»
│   ├── order/           # доменная модель контекста
│   ├── api/             # публичный API контекста (для других контекстов)
│   └── infra/           # персистентность, мессенджеры
├── billing/             # Bounded context «Billing»
│   ├── invoice/
│   ├── api/
│   └── infra/
└── shared/              # shared kernel: только ИСТИННО общее (ID, деньги?)
```

```go
// Каждый контекст публикует минимальный API для соседей.
// Сосед НЕ импортирует internal/ordering/order напрямую.
package api

type OrderConfirmed struct {
	OrderID    string
	TotalCents int64
	Currency   string
}

// Billing подписывается на событие Ordering, а не читает его таблицы.
func (e OrderConfirmed) Event() string { return "order.confirmed" }
```

## Правила

1. **Одна модель на контекст**: «Order» в `ordering` и «Invoice» в `billing` — разные типы, даже если описывают похожие вещи.
2. **Граница = зависимость**: контекст A использует контекст B только через `B/api` или события.
3. **Данные не пересекаются**: каждый контекст владеет своими таблицами; чужие таблицы не читаются.
4. **Shared kernel — под контролем**: общий код только для действительно общего (ID, базовые VO); следить, чтобы он не стал «мусоркой».

## Как находить границы

- Слова, которые значат разное в разных частях системы → разные контексты.
- Команды, которые спорят о модели → границы между ними.
- Доменные процессы (event storming) → естественные контексты.

## Антипаттерны

- ❌ Одна модель на всю систему («у нас же один Order»).
- ❌ Контекст, который читает таблицы соседа «временно».
- ❌ Shared kernel, в который выносят всё «общее».

## Related

- [context-mapping.md](context-mapping.md) — как контексты связаны между собой
- [ubiquitous-language.md](ubiquitous-language.md) — язык внутри контекста
- [../../patterns/modular-monolith.md](../../patterns/modular-monolith.md) — контексты в одном deployable
