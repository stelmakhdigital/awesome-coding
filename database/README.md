# Database — SQL (PostgreSQL) и Redis

Целевые версии (закреплено и проверено на 2026-09-06):
- **PostgreSQL 18** (latest: 18.6); fallback: 17.
- **Redis 8** (latest: 8.10.1); fallback: 8.0.

> SQL/Redis-примеры — рецензированы, не прогонялись на живом сервере.
> Перед применением в критичных местах проверьте `EXPLAIN`.

## Конвенции

- **PostgreSQL** — основной SQL-движок (см. [decisions.md](decisions.md)).
- **Параметризованные запросы** — всегда (см. [shared/security.md](../shared/security.md)).
- **Миграции** — только через инструмент (goose/golang-migrate), не «руками в проде».
- **Redis** — кэш/очереди/структуры данных, не «ещё одна БД» (см. [snippets/redis.md](snippets/redis.md)).

## Структура раздела

- [rules.md](rules.md) — обязательные правила SQL
- [decisions.md](decisions.md) — таблицы решений (SQL vs NoSQL, ORM, кэширование)
- [snippets/](snippets/) — готовые сниппеты:
  - [postgres-core.md](snippets/postgres-core.md) — индексы, EXPLAIN, пулы
  - [transactions.md](snippets/transactions.md) — изоляция, savepoints, advisory locks
  - [migrations.md](snippets/migrations.md) — паттерны миграций (expand-contract)
  - [n-plus-one.md](snippets/n-plus-one.md) — N+1: детект и лечение
  - [redis.md](snippets/redis.md) — кэширование, структуры, TTL
