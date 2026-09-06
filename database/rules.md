---
id: database-rules
title: "Database Rules (SQL/PostgreSQL)"
lang: database
min_version: "18"
category: rule-set
tags: [rules, sql, postgres, indexes, transactions, migrations]
status: stable
updated: 2026-09-06
---

# Database Rules — обязательные правила

## Запросы

- ✅ **Параметризованные запросы** — всегда; конкатенация SQL — только константы.
- ❌ `SELECT *` в production-коде — только нужные колонки (покрытие, читаемость).
- ✅ `EXPLAIN (ANALYZE, BUFFERS)` перед оптимизацией — не «на глаз».
- ✅ Индексы под реальные запросы (из `EXPLAIN`), не «на всякий случай».
- ✅ `LIMIT` на всех списках (даже «внутренних»).
- ✅ Батчи для массовых операций (1000–5000 строк), не один `INSERT` на 100k.

## Индексы

- ✅ B-tree — по умолчанию; GIN/GiST — для поиска/геометрии; BRIN — для упорядоченных больших таблиц.
- ✅ Частичные индексы (`WHERE`) и covering (`INCLUDE`) — для узких запросов.
- ❌ Индекс на каждой колонке (замедляет запись).
- ✅ Проверка использования: `pg_stat_user_indexes` (idx_scan = 0 — кандидат на удаление).

## Транзакции

- ✅ Короткие транзакции: IO/HTTP — вне транзакции.
- ✅ Явная изоляция по умолчанию (`READ COMMITTED`); `SERIALIZABLE` — только когда нужна гарантия.
- ✅ `SAVEPOINT` для откативаемых подшагов.
- ✅ Идемпотентность операций в транзакции (ретраи не дублируют).
- ❌ Держать транзакцию открытой «на время» (блокировки, deadlocks).

## Миграции

- ✅ Только через инструмент (goose/golang-migrate); каждая миграция — `up` + `down`.
- ✅ **Expand-contract** для breaking-изменений схемы (см. [snippets/migrations.md](snippets/migrations.md)).
- ✅ Миграция — атомарная и быстрая (без долгого блокирующего `ALTER` на больших таблицах).
- ❌ «Поправил схему руками в проде».

## Данные

- ✅ `TIMESTAMPTZ` для времени (UTC), не `TIMESTAMP` без зоны (см. [shared/time-and-dates.md](../shared/time-and-dates.md)).
- ✅ Деньги — `NUMERIC` (не `FLOAT`); целые — в минорных единицах (центы) при необходимости.
- ✅ `NOT NULL` + дефолты; `NULL` — только для «неизвестно».
- ✅ UUID/`BIGINT` для PK (UUIDv7 — упорядочиваемый, меньше фрагментации).

## Related

- [decisions.md](decisions.md) — выбор технологий
- [shared/security.md](../shared/security.md) — injection
