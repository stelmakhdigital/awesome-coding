---
id: messaging-consumer-groups
title: "Kafka consumer groups: партицирование, rebalance, идемпотентность, DLQ"
lang: messaging
min_version: "4.3"
category: snippet
tags: [kafka, consumer-group, rebalance, idempotency, dlq, lag]
status: stable
updated: 2026-09-07
---

# Consumer groups

**Когда использовать** — несколько инстансов одного потребителя делят тему; масштабирование обработки.
**Когда НЕ использовать** — «каждому подписчику всё» (тогда разные group.id, по одному consumer'у на подписчика).

## Код (Go, `segmentio/kafka-go`)

```go
r := &kafka.Reader{
	Addr:     kafka.TCP("broker:9092"),
	Topic:    "orders.created",
	GroupID:  "order-processor", // инстансы с одинаковым GroupID делят партишены
	MinBytes: 1,                 // не буферизовать «до 64К»
	MaxBytes: 100_000,
	MaxWait:  500 * time.Millisecond,
}
defer r.Close()

for {
	msg, err := r.FetchMessage(ctx) // внутри — commit после успешной обработки
	if err == io.EOF {
		break
	}
	if err != nil {
		log.Error("fetch", "err", err)
		time.Sleep(time.Second) // reader сам ретраит; не зацикливаться
		continue
	}

	if err := process(ctx, msg); err != nil {
		// Отравленное сообщение: не ретраим бесконечно.
		log.Error("process", "offset", msg.Offset, "err", err)
		sendToDLQ(ctx, msg)            // отдельная тема/очередь + алерт
		_ = r.CommitMessages(ctx, msg) // пропускаем, не зацикливаем группу
		continue
	}
	if err := r.CommitMessages(ctx, msg); err != nil {
		log.Error("commit", "err", err) // дубль при повторе — consumer идемпотентен
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
- **Commit «на всякий случай» до обработки** — потеря событий при краше.
- **Одна тема на всё** (orders, payments, logs в одном топике) — lag и масштабирование
  не управляются; темы — по доменным потокам.

## Related

- [kafka.md](kafka.md)
- [outbox.md](outbox.md)
- [rabbitmq.md](rabbitmq.md)
