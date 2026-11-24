---
id: database-n-plus-one
title: "N+1: детект и лечение"
lang: database
min_version: "18"
category: snippet
tags: [n-plus-one, performance, queries, batching]
status: stable
updated: 2026-11-24
---

# N+1: детект и лечение

**Когда использовать** — отладка медленных списков/страниц; ревью кода с «загрузкой связанных сущностей».
**Когда НЕ использовать** — n/a: диагностический паттерн.

## Что это

1 запрос на список + N запросов на связанные сущности (по одному на элемент).
100 заказов → 101 запрос → 101 round-trip → медленно.

## Детект

```sql
-- Схема примеров ниже.
CREATE TABLE orders (
    id     bigserial PRIMARY KEY,
    status text NOT NULL DEFAULT 'unpaid',
    total  numeric(12,2) NOT NULL
);
CREATE TABLE items (
    id       bigserial PRIMARY KEY,
    order_id bigint NOT NULL REFERENCES orders (id),
    sku      text NOT NULL,
    qty      int    NOT NULL
);
CREATE INDEX items_order_id_idx ON items (order_id); -- без него батч = N индекс-скинов зря
```

```sql
-- Логи запросов (PG): включите log_min_duration_statement.
ALTER SYSTEM SET log_min_duration_statement = '100ms';
-- или: pg_stat_statements — топ по total_exec_time / calls
-- Важно: расширение требует shared_preload_libraries='pg_stat_statements'
-- (postgresql.conf) + рестарт; CREATE EXTENSION — после этого.
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
SELECT query, calls, total_exec_time, mean_exec_time
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
-- признак N+1: высокий calls + низкий mean_time + похожие запросы
```

## Лечение

### 1. Батч (`IN`)

```sql
-- Было (N+1): для каждого заказа:
--   SELECT * FROM items WHERE order_id = $1;

-- Стало (2 запроса):
SELECT * FROM orders WHERE status = 'unpaid' LIMIT 100;
SELECT * FROM items WHERE order_id = ANY(ARRAY[101, 102, 103]); -- id из первого запроса
-- группировка по order_id — в коде
```

### 2. JOIN

```sql
-- Когда связанные данные нужны целиком и один-к-маленькое-N:
SELECT o.id, o.total, i.sku, i.qty
FROM orders o
JOIN items i ON i.order_id = o.id
WHERE o.status = 'unpaid'
LIMIT 100;
-- внимание: LIMIT применяется после join (дубли строк)
```

### 3. Data loader (кэш батчей)

```go
// Package loader — батч-загрузка связанных строк: один запрос на всю страницу.
package loader

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
)

// Items — позиции заказов одним запросом вместо запроса на заказ.
// map заполнен только по заказам с позициями: пустой срез у заказа без позиций —
// норма, а не ошибка.
func Items(ctx context.Context, db *sql.DB, orderIDs []int64) (map[int64][]string, error) {
	if len(orderIDs) == 0 {
		return map[int64][]string{}, nil
	}

	// Плейсхолдеры по числу id: значения уходят как параметры, не как строка.
	placeholders := make([]string, len(orderIDs))
	args := make([]any, len(orderIDs))
	for i, id := range orderIDs {
		placeholders[i] = fmt.Sprintf("$%d", i+1)
		args[i] = id
	}

	rows, err := db.QueryContext(ctx,
		`SELECT order_id, sku
		   FROM order_items
		  WHERE order_id IN (`+strings.Join(placeholders, ",")+`)
		  ORDER BY order_id, id`, args...)
	if err != nil {
		return nil, fmt.Errorf("query items: %w", err)
	}
	defer rows.Close()

	out := make(map[int64][]string, len(orderIDs))
	for rows.Next() {
		var orderID int64
		var sku string
		if err := rows.Scan(&orderID, &sku); err != nil {
			return nil, fmt.Errorf("scan items: %w", err)
		}
		out[orderID] = append(out[orderID], sku)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows items: %w", err)
	}
	return out, nil
}
```

Кэш «в рамках запроса» — это `out` выше: повторное обращение к тому же списку id
берётся из map, а не из БД. Между запросами не кэшируем — иначе отдаём устаревшие
позиции; для повторных страниц кэш нужен явный (см. [redis.md](redis.md)).

### 4. Предрасчёт/материализация

```sql
-- Для отчётов: материализованное представление.
CREATE MATERIALIZED VIEW order_summary AS
SELECT o.id, o.total, count(i.*) AS items_count
FROM orders o
LEFT JOIN items i ON i.order_id = o.id
GROUP BY o.id, o.total;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY order_summary; (по расписанию)
```

## Правила

1. **Один запрос на страницу** — норматив (кроме lazy-загрузок осознанно).
2. **`ANY($1)`/`IN`** — батчи до ~1000 значений (больше — временная таблица).
3. **JOIN + LIMIT** — считать дубли; при большом N — batch предпочтительнее.
4. **ORM**: включить логирование запросов в dev; лимит на число запросов в тесте страницы.

## Related

- [postgres-core.md](postgres-core.md) — EXPLAIN
- [decisions.md — CQRS](../decisions.md)
