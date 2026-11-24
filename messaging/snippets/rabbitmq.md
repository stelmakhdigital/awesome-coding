---
id: messaging-rabbitmq
title: "RabbitMQ: queues, exchanges, ack/nack, DLQ"
lang: messaging
min_version: "4.3"
category: snippet
tags: [rabbitmq, amqp, queue, exchange, dlq, ack]
status: stable
updated: 2026-11-24
---

# RabbitMQ: task queue

**Когда использовать** — обработка задач, routing по типу, приоритеты.
**Когда НЕ использовать** — лог событий/реплей (Kafka).

## Код (Go, `rabbitmq/amqp091-go`)

```go
// Package tasks — RabbitMQ: топология, подтверждённая публикация, потребитель.
package tasks

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"time"

	amqp091 "github.com/rabbitmq/amqp091-go"
)

// Dial — соединение с heartbeat: без них оборванное соединение выглядит живым.
func Dial(url string) (*amqp091.Connection, error) {
	conn, err := amqp091.DialConfig(url, amqp091.Config{Heartbeat: 10 * time.Second})
	if err != nil {
		return nil, fmt.Errorf("amqp dial: %w", err)
	}
	return conn, nil
}

// Topology — декларация идемпотентна: повторный вызов не создаёт дублей.
// Quorum-очередь: x-delivery-limit на classic-очереди не работает.
func Topology(ch *amqp091.Channel) (string, error) {
	if err := ch.ExchangeDeclare("tasks", "topic", true, false, false, false, nil); err != nil {
		return "", fmt.Errorf("exchange tasks: %w", err)
	}
	if err := ch.ExchangeDeclare("dlx", "fanout", true, false, false, false, nil); err != nil {
		return "", fmt.Errorf("exchange dlx: %w", err)
	}
	q, err := ch.QueueDeclare("order.queue", true, false, false, false, amqp091.Table{
		"x-queue-type":           "quorum",
		"x-dead-letter-exchange": "dlx",
		"x-delivery-limit":       3, // после третьей доставки — в DLQ
	})
	if err != nil {
		return "", fmt.Errorf("queue order.queue: %w", err)
	}
	if err := ch.QueueBind(q.Name, "order.created", "tasks", false, nil); err != nil {
		return "", fmt.Errorf("bind order.created: %w", err)
	}
	if _, err := ch.QueueDeclare("order.dlq", true, false, false, false, amqp091.Table{
		"x-queue-type": "quorum",
	}); err != nil {
		return "", fmt.Errorf("queue order.dlq: %w", err)
	}
	return q.Name, nil
}

// Publish — persistent + publisher confirms. Без ожидания подтверждения Publish
// возвращает nil и тогда, когда брокер сообщение не принял.
func Publish(ctx context.Context, ch *amqp091.Channel, task any) error {
	body, err := json.Marshal(task)
	if err != nil {
		return err
	}
	if err := ch.Confirm(false); err != nil {
		return fmt.Errorf("confirm mode: %w", err)
	}
	pub, err := ch.PublishWithDeferredConfirmWithContext(ctx, "tasks", "order.created",
		false, false,
		amqp091.Publishing{
			ContentType:  "application/json",
			DeliveryMode: amqp091.Persistent, // переживёт рестарт брокера
			Body:         body,
			Headers:      amqp091.Table{"schema_version": "1"},
		})
	if err != nil {
		return fmt.Errorf("publish: %w", err)
	}
	// Подтверждение асинхронное: nil от Publish — это «отправлено», а не «принято».
	ackd, err := pub.WaitContext(ctx) // ждём с дедлайном ctx, а не вечно
	if err != nil {
		return fmt.Errorf("confirm: %w", err)
	}
	if !ackd {
		return errors.New("confirm: брокер отклонил сообщение")
	}
	return nil
}

// Consume — prefetch=1 и ручные ack. handle идемпотентен: redelivery возможен.
func Consume(ctx context.Context, ch *amqp091.Channel, queue string,
	handle func(context.Context, []byte) error) error {
	if err := ch.Qos(1, 0, false); err != nil { // не больше одной задачи на потребителя
		return fmt.Errorf("qos: %w", err)
	}
	// С ctx: отмена отменяет подписку и закрывает канал, а не оставляет гонку.
	msgs, err := ch.ConsumeWithContext(ctx, queue, "", false, false, false, false, nil)
	if err != nil {
		return fmt.Errorf("consume: %w", err)
	}
	for m := range msgs {
		if err := handle(ctx, m.Body); err != nil {
			slog.Error("process", "delivery", m.DeliveryTag, "err", err)
			if nErr := m.Nack(false, false); nErr != nil { // requeue=false -> в DLQ
				slog.Error("nack", "delivery", m.DeliveryTag, "err", nErr)
			}
			continue
		}
		if err := m.Ack(false); err != nil {
			slog.Error("ack", "delivery", m.DeliveryTag, "err", err)
		}
	}
	if ctx.Err() != nil {
		return ctx.Err()
	}
	// До сюда доходим, когда канал закрыт при живом ctx (обрыв соединения).
	// Штатным не считается: вызывающий должен переподключиться, иначе
	// потребитель «тихо умер» и очередь растёт.
	return errors.New("amqp: delivery channel closed")
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
8. ❌ `x-delivery-limit` на classic-очереди — лимит доставок есть только у quorum.
9. ❌ Цикл `for m := range msgs` без переподключения: при обрыве соединения канал
   закрывается, потребитель выходит с `nil` и очередь растёт молча.

## Related

- [kafka.md](kafka.md) — лог событий
- [decisions.md](../decisions.md) — выбор
