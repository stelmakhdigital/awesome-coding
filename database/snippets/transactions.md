---
id: database-transactions
title: "PostgreSQL: транзакции, изоляция, advisory locks"
lang: database
min_version: "18"
category: snippet
tags: [postgres, transactions, isolation, savepoint, locks, on-conflict]
status: stable
updated: 2026-11-24
---

# PostgreSQL: транзакции

**Когда использовать** — любые атомарные изменения данных.
**Когда НЕ использовать** — «транзакция» для чтения без изменений (не нужна).

## Базовый паттерн

```sql
-- Схема примеров ниже. Транзакционная целостность — на совести приложения:
-- внешний ключ здесь есть, чтобы кривая вставка упала сразу, а не «потом».
CREATE TABLE accounts (
    id      bigserial PRIMARY KEY,
    balance bigint NOT NULL CHECK (balance >= 0) -- списание ниже упирается в чек, а не в «ушло в минус»
);
INSERT INTO accounts (id, balance) VALUES (42, 500); -- счёт, с которого списываем в примерах
CREATE TABLE transactions (
    id         bigserial PRIMARY KEY,
    account_id bigint NOT NULL REFERENCES accounts (id),
    amount     bigint NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE payments (
    idempotency_key text PRIMARY KEY,
    amount          bigint NOT NULL
);
CREATE TABLE a (id serial PRIMARY KEY);
CREATE TABLE b (id serial PRIMARY KEY);
```

```sql
BEGIN;

UPDATE accounts SET balance = balance - 100 WHERE id = 42;
-- проверить, что затронуто ровно 1 строка (в коде — RowsAffected / GET DIAGNOSTICS)
INSERT INTO transactions (account_id, amount, created_at)
VALUES (42, -100, now());

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
INSERT INTO a (id) VALUES (1);
SAVEPOINT sp1;
INSERT INTO b (id) VALUES (1);   -- может упасть
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
VALUES ('retry-7f3a', 100)
ON CONFLICT (idempotency_key) DO NOTHING; -- повтор: ноль строк, не дубль
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
