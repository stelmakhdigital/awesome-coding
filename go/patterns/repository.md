---
id: go-repository
title: Repository (изоляция доступа к данным)
lang: go
min_version: "1.21"
category: pattern
tags: [architecture, data, sql, interface, di]
status: stable
updated: 2026-09-06
---

# Repository

**Проблема** — бизнес-логика, привязанная к конкретному хранилищу (sql.DB), не тестируется без БД и не меняется без переписывания.
**Решение** — интерфейс-контракт на стороне потребителя; конкретная реализация (SQL, in-memory для тестов) внедряется.
**Когда использовать** — несколько реализаций, тесты без реальной БД, сложная модель данных.
**Когда НЕ использовать** — одна реализация на весь срок жизни проекта и простые запросы: прямой вызов sql.DB допустим (не абстрагируйте «на вырост»).

## Код

```go
package item

import (
	"context"
	"database/sql"
	"errors"
	"sync"
)

// --- Минимальные доменные типы (заглушки для самодостаточности) ---

type Item struct {
	ID   string
	Name string
}

var ErrNotFound = errors.New("not found")

// Контракт определяет ПОТРЕБИТЕЛЬ (сервис), а не реализация.
type Repository interface {
	Get(ctx context.Context, id string) (Item, error)
	List(ctx context.Context, f ListFilter) ([]Item, error)
	Create(ctx context.Context, item Item) error
	Update(ctx context.Context, item Item) error
	Delete(ctx context.Context, id string) error
}

type ListFilter struct {
	Limit  int
	Offset int
	SortBy string
	Desc   bool
}

// Конкретная реализация: SQL.
type SQLRepository struct {
	db *sql.DB
}

func NewSQLRepository(db *sql.DB) *SQLRepository {
	return &SQLRepository{db: db}
}

func (r *SQLRepository) Get(ctx context.Context, id string) (Item, error) {
	row := r.db.QueryRowContext(ctx,
		`SELECT id, name FROM items WHERE id = $1`, id)
	var it Item
	if err := row.Scan(&it.ID, &it.Name); err != nil {
		if err == sql.ErrNoRows {
			return Item{}, ErrNotFound
		}
		return Item{}, err
	}
	return it, nil
}

// ... Create/Update/Delete аналогично.

// Потребитель зависит от интерфейса, а не от sql.DB.
type Service struct {
	items Repository
}

func NewService(items Repository) *Service {
	return &Service{items: items}
}

// В тесте — in-memory реализация того же интерфейса.
type MemRepository struct {
	mu    sync.RWMutex
	items map[string]Item
}
```

## Trade-offs

- **Плюсы**: тестируемость без БД, смена хранилища, явный контракт.
- **Минусы**: лишний слой, риск «анемичного» интерфейса (куча методов-прокси).
- Интерфейс — маленький: только то, что нужно сервису (consumer-defined).
- Альтернатива: `sqlc` — генерация типобезопасного кода из SQL, без ручных репозиториев.

## Related

- [decisions.md — Данные](../decisions.md)
- [snippets/error-handling.md](../snippets/error-handling.md)
