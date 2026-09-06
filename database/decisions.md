---
id: database-decisions
title: "Database Decisions (SQL/NoSQL, ORM, кэширование)"
lang: database
min_version: "18"
category: decisions
tags: [decisions, postgres, nosql, orm, redis, caching]
status: stable
updated: 2026-09-06
---

# Database — таблицы решений

## Движок

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Основной SQL | **PostgreSQL 18** | MySQL 8 | сложные запросы, JSON, полнотекст |
| Простой SQL, экосистема MySQL | MySQL 8 | PostgreSQL | команда знает MySQL |
| Документы (гибкая схема) | PostgreSQL + JSONB | MongoDB | схема меняется, но нужна транзакционность |
| Ключ-значение | Redis | — | кэш, сессии, счётчики |
| Временные ряды | TimescaleDB (расширение PG) | InfluxDB | метрики/телеметрия |

## Доступ к данным

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Go | `database/sql` + `pgx` | GORM | явный SQL, контроль |
| C# | EF Core | Dapper | DDD (см. [csharp/patterns/repository.md](../csharp/patterns/repository.md)) |
| Kotlin | Exposed / SQLDelight | Room (Android) | сервер / локальная БД |
| Python | `psycopg` (3.x) | SQLAlchemy | явный SQL / ORM |
| Сложные read-модели | CQRS: read-модель/материализованные представления | — | отчёты, поиск |

**Правило**: ORM — допустим, но сложные запросы пишутся явным SQL. ORM не заменяет понимание SQL.

## Кэширование (Redis)

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Кэш read-heavy | **Cache-aside** (приложение читает Redis → БД) | write-through | большинство случаев |
| TTL | обязательно (5–30 мин для кэша) | инвалидация по событию | данные меняются редко |
| Сессии/токены | Redis (TTL = время жизни) | — | — |
| Счётчики/рейт-лимиты | Redis (`INCR` + `EXPIRE`, sliding window) | — | — |
| Очередь (лёгкая) | Redis Streams / List | RabbitMQ/Kafka | простые очереди |
| Очередь (надёжная, сложная) | RabbitMQ / Kafka | Redis | DLQ, routing, гарантированная доставка |

**Правило**: Redis — не источник истины. Данные, которые «живут только в Redis», — риск потери.

## Related

- [rules.md](rules.md)
- [messaging/decisions.md](../messaging/decisions.md) — выбор брокера
