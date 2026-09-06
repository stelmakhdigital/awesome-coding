---
id: go-sql
title: "SQL: database/sql + pgx (пул, ctx, транзакции, батчи)"
lang: go
min_version: "1.21"
category: snippet
tags: [sql, postgres, pgx, database, transactions, pool]
status: stable
updated: 2026-09-07
---

# SQL: database/sql + pgx

**Когда использовать** — PostgreSQL из Go: CRUD, транзакции, батчи. `database/sql` + драйвер `pgx/v5/stdlib` — стандарт.
**Когда НЕ использовать** — сложные запросы/миграции с типобезопасностью: `sqlc` (см. [decisions.md](../decisions.md)).

## Код

```go
package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
)

var ErrNotFound = errors.New("not found")

// OpenDB — подключение + проверка пула.
func OpenDB(ctx context.Context, dsn string) (*sql.DB, error) {
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}

	// Лимиты пула — защита БД от шторма соединений.
	// MaxOpenConns ≈ (ядра БД × 2) + 15, для одного сервиса — 20–50.
	db.SetMaxOpenConns(50)
	db.SetMaxIdleConns(10)
	db.SetConnMaxLifetime(time.Hour)
	db.SetConnMaxIdleTime(5 * time.Minute)

	if err := db.PingContext(ctx); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping db: %w", err)
	}
	return db, nil
}

type Item struct {
	ID        int64
	Name      string
	Price     int64 // копейки — деньги в БД как целые
	UpdatedAt time.Time
}

// GetItem — SELECT одной строки; sql.ErrNoRows → ErrNotFound.
func GetItem(ctx context.Context, db *sql.DB, id int64) (Item, error) {
	var it Item
	err := db.QueryRowContext(ctx,
		`SELECT id, name, price, updated_at FROM items WHERE id = $1`, id,
	).Scan(&it.ID, &it.Name, &it.Price, &it.UpdatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return Item{}, ErrNotFound
	}
	if err != nil {
		return Item{}, fmt.Errorf("get item %d: %w", id, err)
	}
	return it, nil
}

// InsertItem — INSERT ... RETURNING (PostgreSQL).
func InsertItem(ctx context.Context, db *sql.DB, name string, price int64) (int64, error) {
	var id int64
	err := db.QueryRowContext(ctx,
		`INSERT INTO items (name, price, updated_at)
		 VALUES ($1, $2, now())
		 RETURNING id`, name, price,
	).Scan(&id)
	if err != nil {
		return 0, fmt.Errorf("insert item %q: %w", name, err)
	}
	return id, nil
}

// UpdateItem — транзакция с проверкой затронутых строк.
func UpdateItem(ctx context.Context, db *sql.DB, id int64, name string, price int64) error {
	res, err := db.ExecContext(ctx,
		`UPDATE items SET name = $1, price = $2, updated_at = now() WHERE id = $3`,
		name, price, id)
	if err != nil {
		return fmt.Errorf("update item %d: %w", id, err)
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

// Transfer — транзакция: два UPDATE атомарно.
func Transfer(ctx context.Context, db *sql.DB, fromID, toID int64, amount int64) error {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	defer func() { _ = tx.Rollback() }() // no-op после Commit.

	if _, err := tx.ExecContext(ctx,
		`UPDATE items SET price = price - $1, updated_at = now() WHERE id = $2`,
		amount, fromID); err != nil {
		return fmt.Errorf("debit: %w", err)
	}
	if _, err := tx.ExecContext(ctx,
		`UPDATE items SET price = price + $1, updated_at = now() WHERE id = $2`,
		amount, toID); err != nil {
		return fmt.Errorf("credit: %w", err)
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit: %w", err)
	}
	return nil
}

// BatchInsert — батч в один запрос (pgx.Batch) для сотен/тысяч строк.
func BatchInsert(ctx context.Context, db *sql.DB, items []struct {
	Name  string
	Price int64
}) error {
	if len(items) == 0 {
		return nil
	}

	// pgx.Batch — драйверный батч: все INSERT уходят одним пакетом.
	// Для database/sql-совместимости: pgxpool + pgx.Batch напрямую.
	// Здесь — компромисс: один мульти-INSERT (до 65535 параметров).
	if len(items) > 5000 {
		return fmt.Errorf("batch too large: %d", len(items))
	}
	query := `INSERT INTO items (name, price, updated_at) VALUES `
	args := make([]any, 0, len(items)*3)
	for i, it := range items {
		if i > 0 {
			query += ", "
		}
		query += fmt.Sprintf("($%d, $%d, now())", i*3+1, i*3+2)
		args = append(args, it.Name, it.Price)
	}
	if _, err := db.ExecContext(ctx, query, args...); err != nil {
		return fmt.Errorf("batch insert %d rows: %w", len(items), err)
	}
	return nil
}
```

## Pitfalls

- **Всегда `*Context`-методы** (`QueryRowContext`, `ExecContext`) — иначе запрос не отменится вместе с ctx.
- `sql.ErrNoRows` — нормальное состояние «нет строки», мапьте в доменную ошибку (`ErrNotFound`), а не в 500.
- `RowsAffected` — проверяйте в UPDATE/DELETE: 0 строк = сущность не найдена/конфликт.
- Деньги — `int64` в минимальных единицах (копейки), не `float64`.
- `defer tx.Rollback()` после `Commit` — no-op, это стандартный приём, не баг.
- Не делайте `db.Query` с циклом по строкам без `rows.Close()` (defer) — соединение остаётся занятым.
- Батч: мульти-INSERT упирается в 65535 параметров на запрос; для больших объёмов — `COPY` или `pgxpool` + `pgx.Batch`.

## Related

- [error-handling.md](error-handling.md)
- [context.md](context.md)
- [decisions.md](../decisions.md)
- [database/snippets/postgres-core.md](../../database/snippets/postgres-core.md)
