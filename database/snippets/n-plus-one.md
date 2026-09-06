---
id: database-n-plus-one
title: "N+1: детект и лечение"
lang: database
min_version: "18"
category: snippet
tags: [n-plus-one, performance, queries, batching]
status: stable
updated: 2026-09-06
---

# N+1: детект и лечение

**Когда использовать** — отладка медленных списков/страниц; ревью кода с «загрузкой связанных сущностей».
**Когда НЕ использовать** — n/a: диагностический паттерн.

## Что это

1 запрос на список + N запросов на связанные сущности (по одному на элемент).
100 заказов → 101 запрос → 101 round-trip → медленно.

## Детект

```sql
-- Логи запросов (PG): включите log_min_duration_statement.
ALTER SYSTEM SET log_min_duration_statement = '100ms';
-- или: pg_stat_statements — топ по total_time / calls
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
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
SELECT * FROM items WHERE order_id = ANY($1); -- $1 = [id1, id2, ...]
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
// DataLoader: собирает id за «тик», один IN-запрос, кэширует результат.
type OrderItemsLoader struct {
    db      *sql.DB
    pending map[string][]func(*sql.Rows)
}

// вызовы внутри одного запроса страницы:
//   items, _ := loader.Items(ctx, orderID) // x100
// → 1 SELECT ... WHERE order_id = ANY(...) на все 100
```

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
3. **JOIN + LIMIT** — считать дубли; при большом N — batч предпочтительнее.
4. **ORM**: включить логирование запросов в dev; лимит на число запросов в тесте страницы.

## Related

- [postgres-core.md](postgres-core.md) — EXPLAIN
- [decisions.md — CQRS](../decisions.md)
