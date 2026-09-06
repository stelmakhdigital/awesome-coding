---
id: database-migrations
title: "Миграции: expand-contract, zero-downtime"
lang: database
min_version: "18"
category: snippet
tags: [migrations, schema, expand-contract, goose, zero-downtime]
status: stable
updated: 2026-09-06
---

# Миграции схемы

**Когда использовать** — любое изменение схемы в production.
**Когда НЕ использовать** — новая БД (просто создайте схему).

## Правила

1. **Инструмент**: goose или golang-migrate (Go), Flyway (Java) — не руками.
2. **Каждая миграция**: `up` + `down`, атомарна, быстра.
3. **Breaking-изменения — expand-contract** (3 шага, 3 деплоя):
   - **Expand**: добавить новое (колонку/таблицу), старое работает.
   - **Migrate**: код пишет в оба места, данные перенесены.
   - **Contract**: убрать старое (колонку/таблицу).
4. **Блокирующие `ALTER`** на больших таблицах — только в окно обслуживания
   (или `ALTER TABLE ... SET ACCESS`-приёмные: PG 11+ — `ALTER` с `NOT VALID` + `VALIDATE`).

## Пример: переименование колонки (expand-contract)

```sql
-- Шаг 1 (expand): добавить новую колонку, бэктрек старыми данными.
ALTER TABLE orders ADD COLUMN customer_name text;
UPDATE orders SET customer_name = customer_full_name;
-- код: пишет в обе колонки (двойная запись).

-- Шаг 2 (migrate): дать время на перенос данных и переключение чтения.
-- (отдельный деплой кода: чтение — только customer_name)

-- Шаг 3 (contract): убрать старую.
ALTER TABLE orders DROP COLUMN customer_full_name;
```

## Пример: новый индекс без блокировки

```sql
-- Создаём асинхронно (не блокирует запись).
CREATE INDEX CONCURRENTLY idx_orders_created ON orders (created_at);
-- проверить: pg_stat_activity / pg_index (indisvalid)
-- при ошибке: DROP INDEX CONCURRENTLY + повторить
```

## Инструменты (Go)

```go
// golang-migrate: миграции в файлах (0001_init.up.sql / 0001_init.down.sql).
// goose: --
// +goose Up
CREATE TABLE orders (id uuid PRIMARY KEY, total numeric(12,2) NOT NULL);
// -- +goose Down
DROP TABLE orders;
```

## Related

- [rules.md — миграции](../rules.md)
- [postgres-core.md](postgres-core.md)
