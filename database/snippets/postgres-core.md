---
id: database-postgres-core
title: "PostgreSQL: индексы, EXPLAIN, пулы соединений"
lang: database
min_version: "18"
category: snippet
tags: [postgres, indexes, explain, pooling, performance]
status: stable
updated: 2026-09-06
---

# PostgreSQL: ядро производительности

**Когда использовать** — оптимизация запросов, выбор индексов, настройка пула.
**Когда НЕ использовать** — n/a: базовый сниппет.

## Индексы

```sql
-- B-tree (по умолчанию): equality + range + sort.
CREATE INDEX idx_orders_status ON orders (status);

-- Частичный: только интересующие строки (меньше размер, быстрее).
CREATE INDEX idx_orders_unpaid ON orders (customer_id) WHERE status = 'unpaid';

-- Covering: запрос обслуживается из индекса (Index Only Scan).
CREATE INDEX idx_orders_customer ON orders (customer_id) INCLUDE (total, status);

-- GIN: JSONB и полнотекст.
CREATE INDEX idx_events_payload ON events USING gin (payload jsonb_path_ops);

-- Многостолбцовый: порядок колонок = порядок условий запроса.
CREATE INDEX idx_orders_customer_status ON orders (customer_id, status);
```

## EXPLAIN

```sql
-- Всегда перед «оптимизацией на глаз».
EXPLAIN (ANALYZE, BUFFERS)
SELECT o.id, o.total
FROM orders o
WHERE o.customer_id = $1 AND o.status = 'unpaid'
ORDER BY o.created_at DESC
LIMIT 20;

-- На что смотреть:
--   Seq Scan на большой таблице      -> нужен индекс
--   Sort (top-N heapsort)            -> хорошо; external merge -> не хватает памяти
--   Nested Loop с большим внутренним -> проверить join-условие
--   Buffers: shared hit/read         -> кэш или диск
```

## Пулы соединений

```sql
-- Мониторинг: сколько соединений, сколько ждёт.
SELECT count(*) AS total,
       count(*) FILTER (WHERE state = 'active') AS active,
       count(*) FILTER (WHERE state = 'idle') AS idle
FROM pg_stat_activity
WHERE datname = current_database();
```

Правила пула (pgbouncer / pgxpool):

| Параметр | Рекомендация | Почему |
|---|---|---|
| Размер пула | `cores * 2 + effective_spindle_count` (правило PG) | больше — не быстрее (контекст-свитчи) |
| `idle_in_transaction_session_timeout` | 60–300s | не держать транзакции открытыми |
| Режим pgbouncer | `transaction` (не `session`) | больше переиспользования |
| Таймауты | acquire < 5s, query < 30s | fail fast |

## Массовые операции

```sql
-- Батч INSERT (1000–5000 строк), не по одной.
INSERT INTO events (id, payload, created_at)
VALUES
  ($1, $2, now()),
  ($3, $4, now()),
  ...
ON CONFLICT (id) DO NOTHING; -- идемпотентность

-- Массовое обновление: батчами по PK, чтобы не блокировать.
UPDATE events SET processed = true
WHERE id IN (SELECT id FROM events WHERE processed = false ORDER BY id LIMIT 5000);
-- повторять, пока затронуто > 0
```

## Related

- [transactions.md](transactions.md) — изоляция и блокировки
- [n-plus-one.md](n-plus-one.md) — N+1
- [rules.md](../rules.md)
