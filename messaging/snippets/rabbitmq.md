---
id: messaging-rabbitmq
title: "RabbitMQ: queues, exchanges, ack/nack, DLQ"
lang: messaging
min_version: "4.3"
category: snippet
tags: [rabbitmq, amqp, queue, exchange, dlq, ack]
status: stable
updated: 2026-09-06
---

# RabbitMQ: task queue

**Когда использовать** — обработка задач, routing по типу, приоритеты.
**Когда НЕ использовать** — лог событий/реплей (Kafka).

## Код (Go, `rabbitmq/amqp091-go`)

```go
// Topology: exchange -> queue (routing key), DLQ для ошибок.
//   tasks (topic exchange) --order.created--> order.queue
//   order.queue (x-dead-letter-exchange) --> dlx --> order.dlq

conn, err := amqp091.Dial("amqp://user:pass@host:5672/")
if err != nil {
    return err
}
defer conn.Close()
ch, err := conn.Channel()
if err != nil {
    return err
}

// Идемпотентная топология (Declare — не создаёт дубли).
if err := ch.ExchangeDeclare("tasks", "topic", true, false, false, false, nil); err != nil {
    return err
}
if err := ch.ExchangeDeclare("dlx", "fanout", true, false, false, false, nil); err != nil {
    return err
}
q, err := ch.QueueDeclare("order.queue", true, false, false, false, amqp091.Table{
    "x-dead-letter-exchange": "dlx", // после 3 nack -> DLQ
    "x-delivery-limit":       3,
})
if err != nil {
    return err
}
if err := ch.QueueBind(q.Name, "order.created", "tasks", false, nil); err != nil {
    return err
}
if _, err := ch.QueueDeclare("order.dlq", true, false, false, false, nil); err != nil {
    return err
}

// Producer: persistent + confirmed.
err = ch.PublishWithContext(ctx, "tasks", "order.created",
    true,  // persistent: переживёт рестарт брокера
    false,
    amqp091.Publishing{
        ContentType:  "application/json",
        DeliveryMode: amqp091.Persistent,
        Body:         mustMarshal(task),
        Headers:      amqp091.Table{"schema_version": "1"},
    })

// Consumer: prefetch=1, ручные ack.
ch.Qos(1, 0, false) // prefetch: не перегружать потребителя
msgs, err := ch.Consume(q.Name, "", false, false, false, false, nil)
for m := range msgs {
    if err := process(ctx, m.Body); err != nil {
        log.Error("process", "err", err)
        // Nack + requeue=false: в DLQ (после delivery-limit)
        m.Nack(false, false)
        continue
    }
    m.Ack(false)
}
```

## Правила

1. **Prefetch** — всегда (иначе один «жадный» потребитель забирает всё).
2. **Persistent** для задач, которые нельзя потерять; `confirmed` publisher — знать об успехе.
3. **Начальные значения топологии** — в коде (idempotent declare), не «руками в UI».
4. **DLQ + алерт**: сообщения в DLQ — инцидент, не «нормальная работа».
5. **Идемпотентность**: redelivery после сбоев возможна.
6. **Мониторинг**: размер очереди (главная метрика), consumers, unacked.
7. ❌ `autoAck: true` — сообщение теряется при сбое обработчика.

## Related

- [kafka.md](kafka.md) — лог событий
- [decisions.md](../decisions.md) — выбор
