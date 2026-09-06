---
id: database-transactions
title: "PostgreSQL: транзакции, изоляция, advisory locks"
lang: database
min_version: "18"
category: snippet
tags: [postgres, transactions, isolation, savepoint, locks]
status: stable
updated: 2026-09-06
---

# PostgreSQL: транзакции

**Когда использовать** — любые атомарные изменения данных.
**Когда НЕ использовать** — «транзакция» для чтения без изменений (не нужна).

## Базовый паттерн

```sql
BEGIN;

UPDATE accounts SET balance = balance - $1 WHERE id = $2;
-- проверить, что затронуто 1 строка (GET DIAGNOSTICS row_count)
INSERT INTO transactions (account_id, amount, created_at)
VALUES ($2, -$1, now());

COMMIT;
-- ROLLBACK при ошибке (явно или по таймауту)
```

## Изоляция

| Уровень | Что даёт | Когда |
|---|---|---|
| `READ COMMITTED` (default) | читаем только закоммиченное | 95% случаев |
| `REPEATABLE READ` | snapshot на момент первой команды | отчёты «как на момент X» |
| `SERIALIZABLE` | без аномалий, но retry на конфликте | деньги, строгие инварианты |

```sql
-- SERIALIZABLE + обработка сериализационных конфликтов (код 40001).
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
-- при ошибке 40001 — повторить транзакцию (идемпотентно!)
```

## Savepoint

```sql
BEGIN;
INSERT INTO a (...) VALUES (...);
SAVEPOINT sp1;
INSERT INTO b (...) VALUES (...); -- может упасть
ROLLBACK TO sp1;                  -- откатить только вставку в b
COMMIT;                           -- вставка в a сохраняется
```

## Advisory locks (межсоединительные)

```sql
-- Блокировка «одного воркера» для задачи (например, миграция/репорт).
SELECT pg_advisory_xact_lock(hashtext('nightly_report'));
-- блокируется до COMMIT/ROLLBACK текущей транзакции
```

## Идемпотентность

```sql
-- Ретрай не должен дублировать: unique-ключ + ON CONFLICT.
INSERT INTO payments (idempotency_key, amount)
VALUES ($1, $2)
ON CONFLICT (idempotency_key) DO NOTHING;
```

## Правила

1. **Короткие транзакции**: HTTP/IO — до или после, не внутри.
2. **`idle_in_transaction_session_timeout`** — страховка от «забытых» транзакций.
3. **Один владелец блокировки**: не «двое пишут в одну строку».
4. **Deadlock**: одинаковый порядок блокировок во всех кодовых путях.
5. **`SELECT ... FOR UPDATE`** — только когда нужна блокировка строки (иначе — race).

## Related

- [postgres-core.md](postgres-core.md) — пулы
- [migrations.md](migrations.md) — миграции и блокировки
