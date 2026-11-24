# Messaging — брокеры сообщений

Целевые версии (закреплено и проверено на 2026-09-06):
- **Apache Kafka 4.3** (latest: 4.3.1); fallback: 4.2.
- **RabbitMQ 4.3** (latest: 4.3.5); fallback: 4.0.

> Брокеры — отдельный раздел от [database/](../database/): это не хранилище данных,
> а транспорт событий/сообщений (другие гарантии, другие паттерны).

## Правила

Обязательные guardrails — в [rules.md](rules.md) (доставка и идемпотентность,
отказоустойчивость, порядок, схема сообщения, конфигурация брокера).

## Структура раздела

- [rules.md](rules.md) — обязательные правила (✅/❌)
- [decisions.md](decisions.md) — Kafka vs RabbitMQ vs Redis Streams
- [snippets/kafka.md](snippets/kafka.md) — producer/consumer, exactly-once, consumer groups
- [snippets/rabbitmq.md](snippets/rabbitmq.md) — queues, exchanges, ack/nack, DLQ
