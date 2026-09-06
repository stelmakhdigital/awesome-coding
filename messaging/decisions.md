---
id: messaging-decisions
title: "Messaging Decisions (Kafka vs RabbitMQ vs Redis Streams)"
lang: messaging
min_version: null
category: decisions
tags: [decisions, kafka, rabbitmq, redis-streams, broker, choices]
status: stable
updated: 2026-09-06
---

# Messaging — таблицы решений

## Выбор брокера

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Лог событий / event sourcing | **Kafka** | — | append-only, реплей, retention |
| Высокий throughput, репликация | **Kafka** | — | миллионы msg/s |
| Task queue (обработка задач) | **RabbitMQ** | Kafka | routing, приоритеты, ack |
| Сложный routing (fanout/topic) | **RabbitMQ** (exchanges) | Kafka (только по ключу) | разные обработчики по типу |
| Простая очередь в одном приложении | Redis Streams / List | — | нет отдельного кластера |
| Встроенный канал (Go) | `chan` | — | в пределах процесса |

## Гарантии доставки

| Режим | Что значит | Когда |
|---|---|---|
| at-most-once | потеря допустима | метрики, телеметрия |
| **at-least-once** (default) | дубли возможны | большинство случаев → идемпотентность |
| exactly-once | без дублей | Kafka transactions (producer+consumer), дорого |

**Правило**: проектируйте под at-least-once + идемпотентность; exactly-once — только когда цена дубля выше цены сложности.

## Паттерны

| Паттерн | Суть | Файл |
|---|---|---|
| Outbox | событие пишется в БД вместе с данными, relay отправляет в брокер | [architecture/patterns/event-driven.md](../architecture/patterns/event-driven.md) |
| DLQ | необработанные сообщения — в dead letter queue + алерт | [snippets/rabbitmq.md](snippets/rabbitmq.md) |
| Consumer group | N потребителей, каждое сообщение — одному | [snippets/kafka.md](snippets/kafka.md) |
| Schema registry | контракт сообщения (Avro/JSON Schema) | decisions |

## Related

- [database/decisions.md](../database/decisions.md) — Redis как лёгкая очередь
- [architecture/patterns/event-driven.md](../architecture/patterns/event-driven.md)
