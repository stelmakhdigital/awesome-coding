---
id: messaging-consumer-groups
title: "Kafka consumer groups: партицирование, rebalance, идемпотентность, DLQ"
lang: messaging
min_version: "4.3"
category: snippet
tags: [kafka, consumer-group, rebalance, idempotency, dlq, lag]
status: stable
updated: 2026-11-24
---

# Consumer groups

**Когда использовать** — несколько инстансов одного потребителя делят тему; масштабирование обработки.
**Когда НЕ использовать** — «каждому подписчику всё» (тогда разные group.id, по одному consumer'у на подписчика).

## Код (Go, `segmentio/kafka-go`)

```go
// Package consumer — потребитель Kafka: группа, commit после обработки, DLQ.
package consumer

import (
	"context"
	"errors"
	"io"
	"log/slog"
	"time"

	"github.com/segmentio/kafka-go"
)

// NewReader — читатель с явными настройками выборки. Читатель создаётся через
// ReaderConfig: у kafka.Reader открытых полей конфигурации нет.
func NewReader(broker, topic, groupID string) *kafka.Reader {
	return kafka.NewReader(kafka.ReaderConfig{
		Brokers:  []string{broker},
		Topic:    topic,
		GroupID:  groupID, // инстансы с одинаковым GroupID делят партишены
		MinBytes: 1,       // не буферизовать «до 64К», иначе ждём пачку
		MaxBytes: 100_000,
		MaxWait:  500 * time.Millisecond,
	})
}

// Run читает до отмены ctx: обработка -> commit. Ошибка обработки -> DLQ -> commit.
// Commit на успехе обработки = доставка «не менее одного раза»: handle идемпотентен.
func Run(ctx context.Context, r *kafka.Reader,
	handle func(context.Context, kafka.Message) error,
	dlq func(context.Context, kafka.Message) error) {
	defer r.Close()

	for {
		msg, err := r.FetchMessage(ctx)
		if errors.Is(err, io.EOF) || errors.Is(err, context.Canceled) {
			return
		}
		if err != nil {
			slog.Error("fetch", "err", err)
			select {
			case <-ctx.Done():
				return
			case <-time.After(time.Second): // читатель ретраит сам; без паузы закрутимся
			}
			continue
		}

		if err := handle(ctx, msg); err != nil {
			slog.Error("process", "offset", msg.Offset, "err", err)
			if dErr := dlq(ctx, msg); dErr != nil {
				// В DLQ не попали и коммитим — сообщение потеряно. Не коммитим:
				// оно придёт снова (после ребаланса или перезапуска).
				slog.Error("dlq", "offset", msg.Offset, "err", dErr)
				continue
			}
			// Отравленное сообщение ушло в DLQ: пропускаем, не зацикливаем группу.
		}

		if err := r.CommitMessages(ctx, msg); err != nil {
			slog.Error("commit", "offset", msg.Offset, "err", err)
		}
	}
}
```

## Правила

1. **Один `GroupID` = один логический потребитель**. Инстансы с одинаковым ID делят
   партишены; разные ID — каждый получает всё (fan-out).
2. **Ключ = сущность** (producer: hash по ключу): порядок на сущность гарантирован;
   разные сущности — параллельно по партишнам.
3. **Число инстансов ≤ число партишенов**: лишний инстанс простаивает.
   Масштабирование = сначала партишены, потом инстансы.
4. **Commit после обработки** (не до). Дубли возможны (crash между обработкой и commit) —
   **consumer идемпотентен**: upsert / idempotency key / проверка состояния.
5. **Rebalance — не баг**: при старте/смерти инстансов партишины перераспределяются
   (stop-the-world на тему). Уменьшите частоту: `session.timeout`/`heartbeat.interval`
   разумные, батчи — не крошечные.
6. **Lag — главная метрика**: `consumer lag` по группе + алерт; lag растёт —
   либо добавить инстансы, либо ускорить обработку.

## Идемпотентность (практика)

```sql
-- Таблица обработанных событий (TTL-очистка):
CREATE TABLE processed_events (
    event_id   TEXT PRIMARY KEY,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- process(): INSERT ... ON CONFLICT (event_id) DO NOTHING;
--            если RowsAffected = 0 — событие уже обработано, пропускаем.
```

## Pitfalls

- **Блокирующая обработка в consumer**: один медленный message тормозит партишн
  (и lag). Тяжёлая работа — в пул/очередь, consumer — тонкий.
- **Rebalance-шторм**: короткие session timeout'ы + медленный старт инстансов =
  постоянные rebalance. Ставьте timeout с запасом.
- **DLQ без алерта** — сообщения «теряются» в мёртвой очереди.
- **Commit после неудачной отправки в DLQ** — сообщение ни обработано, ни в DLQ: потеряно. Не коммитим — пусть придёт снова.
- **Commit «на всякий случай» до обработки** — потеря событий при краше.
- **Одна тема на всё** (orders, payments, logs в одном топике) — lag и масштабирование
  не управляются; темы — по доменным потокам.

## Related

- [kafka.md](kafka.md)
- [outbox.md](outbox.md)
- [rabbitmq.md](rabbitmq.md)
