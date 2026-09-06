---
id: messaging-kafka
title: "Kafka: producer, consumer, consumer groups"
lang: messaging
min_version: "4.3"
category: snippet
tags: [kafka, producer, consumer, consumer-group, exactly-once]
status: stable
updated: 2026-09-06
---

# Kafka: producer и consumer

**Когда использовать** — лог событий, high-throughput, реплей, event-driven.
**Когда НЕ использовать** — простая task queue с routing (RabbitMQ проще).

## Код (Go, `segmentio/kafka-go`)

```go
// Producer: с подтверждением всех ISR-реплик.
w := &kafka.Writer{
    Addr:         kafka.TCP("broker:9092"),
    Topic:        "orders.created",
    Balancer:     &kafka.Hash{}, // по ключу -> один партишн на сущность
    RequiredAcks: kafka.RequireAll, // все ISR-реплики подтвердили запись
}
defer w.Close()

err := w.WriteMessages(ctx,
    kafka.Message{
        Key:   []byte(orderID), // partitioning: один заказ -> один партишн
        Value: mustMarshal(orderEvent),
        Headers: []kafka.Header{
            {Key: "schema_version", Value: []byte("1")},
        },
    },
)

// Consumer: consumer group, at-least-once, ручное подтверждение.
r := kafka.NewReader(kafka.ReaderConfig{
    Brokers:   []string{"broker:9092"},
    Topic:     "orders.created",
    GroupID:   "order-processor",
    MinBytes:  1, // не ждать батч
    MaxBytes:  1e6,
})
defer r.Close()

for {
    msg, err := r.FetchMessage(ctx)
    if err == io.EOF {
        continue // пересоединение
    }
    if err != nil {
        log.Error("fetch", "err", err)
        continue
    }
    if err := process(ctx, msg.Value); err != nil {
        log.Error("process", "err", err, "key", string(msg.Key))
        // сообщение НЕ подтверждено -> будет доставлено повторно
        // (идемпотентная обработка обязательна!)
        continue
    }
    if err := r.CommitMessages(ctx, msg); err != nil {
        log.Error("commit", "err", err)
    }
}
```

## Правила

1. **Ключ = идентификатор сущности**: порядок внутри сущности гарантирован (один партишн).
2. **Идемпотентность потребителя**: дубли возможны (at-least-once) — `processed_ids`/unique-ключ.
3. **Schema version в заголовке**: consumers читают старые версии при ретраях.
4. **Retention** — осознанно: лог событий — 7–30 дней, не «навсегда».
5. **Мониторинг**: consumer lag (главная метрика!), under-replicated partitions.
6. ❌ `FetchMessage` в цикле без обработки ошибок — «молча упавший» consumer.

## Exactly-once (когда нужно)

```go
// Producer transactions + idempotent consumer:
// 1. producer: BeginTransaction -> WriteMessages (topic + reply topic) -> CommitTransaction
// 2. consumer: в той же транзакции читает и пишет
// Дорого и сложно: только для финансовых операций.
```

## Related

- [rabbitmq.md](rabbitmq.md) — task queue
- [decisions.md](../decisions.md) — выбор брокера
