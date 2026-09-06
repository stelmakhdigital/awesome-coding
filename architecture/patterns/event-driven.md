---
id: arch-event-driven
title: "Архитектура: Event-Driven"
lang: shared
min_version: "1.21"
category: pattern
tags: [architecture, event-driven, outbox, messaging, advanced, go]
status: experimental
updated: 2026-09-06
---

# Event-Driven Architecture

Компоненты общаются **событиями** (асинхронно), а не вызовами.
Публикатор не знает подписчиков; подписчик не знает, кто опубликовал.

**Когда использовать** — слабая связанность модулей, интеграции с внешними системами,
отказоустойчивость (потребитель может быть недоступен), независимые деплои.
**Когда НЕ использовать** — «нужен ответ прямо сейчас» (это вызов, не событие);
простая последовательность внутри одного сервиса (прямой вызов проще).

## Ключевые паттерны

| Паттерн | Смысл |
|---|---|
| **Event Notification** | Событие несёт только факт; потребитель сам запрашивает данные |
| **Event-Carried State Transfer** | Событие несёт данные; потребитель не ходит за ними |
| **Outbox** | Надёжная публикация: событие пишется в БД вместе с изменением, relay доставляет |

## Правила

1. **Eventual consistency** — базовое допущение: потребитель может обработать событие позже.
2. **Идемпотентность потребителя**: дубли событий возможны (at-least-once доставка).
3. **Outbox — по умолчанию** для критичных событий: «записал в БД, но не опубликовал» недопустимо.
4. **Порядок**: внутри одного потока (агрегата) порядок гарантируется; между потоками — нет.
5. **Tracing**: correlation/trace ID в каждом событии.

## Код (Go) — Outbox

```go
package outbox

import (
	"context"
	"database/sql"
)

// Publisher: шина (NATS/Kafka/...) — интерфейс, реализация в инфраструктуре.
type Publisher interface {
	Publish(ctx context.Context, eventType string, payload []byte) error
}

// Outbox: событие пишется в ту же транзакцию, что и изменение.
// Relay (отдельный воркер) публикует из таблицы в шину и помечает published.
type Outbox struct {
	db *sql.DB
}

type PendingEvent struct {
	StreamID  string
	EventType string
	Payload   []byte
	Published bool
}

// AppendInTx: вызывается ВНУТРИ той же транзакции, что и изменение данных.
func (o *Outbox) AppendInTx(ctx context.Context, tx *sql.Tx, streamID, eventType string, payload []byte) error {
	_, err := tx.ExecContext(ctx,
		`INSERT INTO outbox (stream_id, event_type, payload) VALUES ($1, $2, $3)`,
		streamID, eventType, payload)
	return err
}

// Relay: публикует неотправленные события (at-least-once: дубли возможны,
// поэтому потребители должны быть идемпотентны).
func (o *Outbox) PublishPending(ctx context.Context, bus Publisher, limit int) error {
	rows, err := o.db.QueryContext(ctx,
		`SELECT id, stream_id, event_type, payload FROM outbox
		 WHERE NOT published ORDER BY id LIMIT $1 FOR UPDATE SKIP LOCKED`, limit)
	if err != nil {
		return err
	}
	defer rows.Close()
	var ids []int64
	for rows.Next() {
		var id int64
		var e PendingEvent
		if err := rows.Scan(&id, &e.StreamID, &e.EventType, &e.Payload); err != nil {
			return err
		}
		if err := bus.Publish(ctx, e.EventType, e.Payload); err != nil {
			return err // не пометили published — повторим в следующем цикле
		}
		ids = append(ids, id)
	}
	for _, id := range ids {
		if _, err := o.db.ExecContext(ctx, `UPDATE outbox SET published = true WHERE id = $1`, id); err != nil {
			return err
		}
	}
	return nil
}
```

## Антипаттерны

- ❌ Публикация «из кода» без outbox: транзакция откатилась, а событие ушло (или наоборот).
- ❌ Потребитель без идемпотентности: дубль события = дубль действия.
- ❌ «Событие» для синхронного request/response (это API, не событие).
- ❌ Зависимость от порядка событий между разными потоками.

## Related

- [event-sourcing.md](event-sourcing.md) — события как хранилище
- [cqrs.md](cqrs.md) — события для read-моделей
- [microservices.md](microservices.md) — интеграция сервисов
- [../ddd/tactical/domain-event.md](../ddd/tactical/domain-event.md)
