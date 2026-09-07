# Messaging — сниппеты

| Сниппет | Суть | Файл |
|---|---|---|
| Kafka | producer/consumer, consumer groups, exactly-once | [kafka.md](kafka.md) |
| RabbitMQ | queues, exchanges, ack/nack, DLQ | [rabbitmq.md](rabbitmq.md) |
| Outbox | события из транзакции: DDL, публикация, relay, правила | [outbox.md](outbox.md) |
| Consumer groups | партицирование, rebalance, идемпотентность, DLQ | [consumer-groups.md](consumer-groups.md) |

Код (Go): `kafka.md`, `rabbitmq.md` — скомпилирован (Go 1.27.1); клиенты: `segmentio/kafka-go`,
`rabbitmq/amqp091-go` (v1.14.0). `outbox.md`, `consumer-groups.md` — gofmt-чисто, рецензированы.
