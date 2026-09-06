# Messaging — брокеры сообщений

Целевые версии (закреплено и проверено на 2026-09-06):
- **Apache Kafka 4.3** (latest: 4.3.1); fallback: 4.2.
- **RabbitMQ 4.3** (latest: 4.3.5); fallback: 4.0.

> Брокеры — отдельный раздел от [database/](../database/): это не хранилище данных,
> а транспорт событий/сообщений (другие гарантии, другие паттерны).

## Конвенции

- **Код — идемпотентный**: дубликаты сообщений возможны (at-least-once) — обработка не дублирует.
- **Outbox pattern** для «запись в БД + событие атомарно» (см. [architecture/patterns/event-driven.md](../architecture/patterns/event-driven.md)).
- **Контракт сообщения** — документирован (схема + версия), breaking changes — новая тема/версия.
- **DLQ (dead letter queue)** — обязательна для очередей с обработкой.

## Структура раздела

- [decisions.md](decisions.md) — Kafka vs RabbitMQ vs Redis Streams
- [snippets/kafka.md](snippets/kafka.md) — producer/consumer, exactly-once, consumer groups
- [snippets/rabbitmq.md](snippets/rabbitmq.md) — queues, exchanges, ack/nack, DLQ
