---
id: messaging-kafka
title: "Kafka: producer (acks=all, порядок на сущность, версия схемы)"
lang: messaging
min_version: "4.3"
category: snippet
tags: [kafka, producer, consumer, consumer-group, exactly-once]
status: stable
updated: 2026-11-24
---

# Kafka: producer

**Когда использовать** — лог событий, high-throughput, реплей, event-driven.
**Когда НЕ использовать** — простая task queue с routing (RabbitMQ проще).

## Продюсер (Go, `segmentio/kafka-go`)

```go
// Package orders — продюсер темы заказов: порядок на сущность, подтверждение от ISR.
package orders

import (
	"context"
	"encoding/json"
	"time"

	"github.com/segmentio/kafka-go"
)

// NewWriter — продюсер с подтверждением от всех ISR-реплик.
// Без этого брокер отвечает до записи в реплики: событие переживёт рестарт
// лидера только если повезёт.
func NewWriter(broker, topic string) *kafka.Writer {
	return &kafka.Writer{
		Addr:         kafka.TCP(broker),
		Topic:        topic,
		Balancer:     &kafka.Hash{}, // по ключу: один партишн на сущность
		RequiredAcks: kafka.RequireAll,
		BatchTimeout: 10 * time.Millisecond,
	}
}

// Publish — событие с версией схемы в заголовке: потребители читают старые
// версии при ретраях, поэтому версия должна быть видна без разбора тела.
func Publish(ctx context.Context, w *kafka.Writer, key string, event any) error {
	value, err := json.Marshal(event)
	if err != nil {
		return err
	}
	return w.WriteMessages(ctx, kafka.Message{
		Key:     []byte(key), // partitioning: один заказ -> один партишн
		Value:   value,
		Headers: []kafka.Header{{Key: "schema_version", Value: []byte("1")}},
	})
}
```

Потребитель (группа, commit после обработки, DLQ) —
[consumer-groups.md](consumer-groups.md): там цикл с обработкой ошибок и отравленными
сообщениями, здесь только продюсер.

## Правила

1. **Ключ = идентификатор сущности**: порядок внутри сущности гарантирован (один партишн).
2. **Идемпотентность потребителя**: дубли возможны (at-least-once) — `processed_ids`/unique-ключ.
3. **Schema version в заголовке**: consumers читают старые версии при ретраях.
4. **Retention** — осознанно: лог событий — 7–30 дней, не «навсегда».
5. **Мониторинг**: consumer lag (главная метрика!), under-replicated partitions.
6. ❌ `FetchMessage` в цикле без паузы на ошибке — consumer крутится без сна
   и пишет лог до отказа диска (пауза/backoff — в [consumer-groups.md](consumer-groups.md)).

## Exactly-once (когда нужно)

```text
producer: BeginTransaction -> WriteMessages (topic + reply topic) -> CommitTransaction
consumer: читает и пишет в той же транзакции
```

Дорого и сложно (транзакционный идемпотентный продюсер, `transactional.id`,
`isolation.level=read_committed`). Только для финансовых операций; чаще дешевле
идемпотентный потребитель + уникальный ключ обработки.

## Related

- [rabbitmq.md](rabbitmq.md) — task queue
- [decisions.md](../decisions.md) — выбор брокера
