# Database — сниппеты

| Сниппет | Суть | Файл |
|---|---|---|
| PostgreSQL core | индексы, EXPLAIN, пулы соединений | [postgres-core.md](postgres-core.md) |
| Transactions | изоляция, savepoints, advisory locks, идемпотентность | [transactions.md](transactions.md) |
| Migrations | expand-contract, zero-downtime, `CONCURRENTLY` | [migrations.md](migrations.md) |
| N+1 | детект (`pg_stat_statements`) и 4 способа лечения | [n-plus-one.md](n-plus-one.md) |
| Redis | cache-aside, TTL, структуры данных, rate limit | [redis.md](redis.md) |
| Пагинация | keyset против OFFSET, непрозрачный курсор | [pagination.md](pagination.md) |

SQL в этих файлах выполняется на PostgreSQL 18 (`make verify`), Go-блоки собираются
go build 1.27. Что именно доказывает уровень — в [../../docs/FORMAT.md](../../docs/FORMAT.md).
