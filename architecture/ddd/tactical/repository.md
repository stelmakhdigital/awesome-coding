---
id: ddd-repository
title: DDD: Repository
lang: shared
min_version: "1.21"
category: pattern
tags: [ddd, repository, persistence, go]
status: stable
updated: 2026-09-06
---

# Repository (репозиторий)

Коллекция агрегатов в памяти: скрывает персистентность, домен работает с интерфейсом.
**Один repository — на один агрегат** (не на таблицу!).

**Когда использовать** — любой уровень DDD ≥ 1; на уровне 0 допустим «упрощённый»
repository (см. [go/patterns/repository.md](../../../go/patterns/repository.md)).
**Когда НЕ использовать** — сложное чтение (отчёты, поиск): это read-side / query service,
а не repository домена.

## Код (Go)

```go
package order

import "context"

// Минимальные определения для примера (полная модель — в entity.md/aggregate.md).
type OrderID string

type Order struct {
	id OrderID
}

// Repository: интерфейс в домене, реализация — в инфраструктуре.
// Направление зависимости: infra → domain (реализация зависит от интерфейса).
type OrderRepository interface {
	Get(ctx context.Context, id OrderID) (*Order, error)
	Save(ctx context.Context, o *Order) error // insert или update
	Delete(ctx context.Context, id OrderID) error
}

// Пример реализации (инфраструктурный слой, sqlc/наш SQL):
//
// type sqlOrderRepository struct {
//     db *sql.DB
// }
//
// func (r *sqlOrderRepository) Get(ctx context.Context, id OrderID) (*Order, error) {
//     // SELECT ...; восстановление доменной модели (валидация инвариантов)
// }
```

## Правила

1. **На агрегат, не на таблицу**: `OrderRepository` — да, `OrderItemRepository` — нет
   (позиции заказа живут внутри агрегата `Order`).
2. **Возвращает агрегаты**, а не DTO/карты строк: восстановление модели — часть Get.
3. **Save = insert или update** (или явно `Add`/`Update` — выберите и держитесь).
4. **Домен не знает SQL/ORM**: только интерфейс.
5. **Сложные запросы — не сюда**: отчёты и поиск — read-side (CQRS) или query service.

## Антипаттерны

- ❌ Repository на каждую таблицу с SQL-логикой в домене.
- ❌ Возврат DTO/`map[string]any` вместо доменных объектов.
- ❌ «Умный» repository, который меняет состояние агрегата (это поведение модели).
- ❌ Домен, импортирующий драйвер БД ради «удобства».

## Related

- [go/patterns/repository.md](../../../go/patterns/repository.md) — конкретная реализация на Go (sqlc, транзакции)
- [aggregate.md](aggregate.md) — что именно хранится
- [cqrs.md](../../patterns/cqrs.md) — когда читать лучше не через repository
