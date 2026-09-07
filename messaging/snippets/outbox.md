---
id: messaging-outbox
title: "Outbox: события из транзакции без потери и дублей"
lang: messaging
min_version: "4.3"
category: pattern
tags: [outbox, events, transaction, reliability, cdc, kafka]
status: stable
updated: 2026-09-07
---

# Outbox pattern

**Когда использовать** — «изменить данные в БД И опубликовать событие» должно быть атомарно:
заказ создан → событие `orders.created`; откат транзакции → события не было.
**Когда НЕ использовать** — события без связи с данными (метрики, логи); «событие — это и есть запись» (event sourcing).

## Проблема (почему не «два вызова»)

```
1) UPDATE orders ...;      -- коммит
2) kafka.Publish(...)       -- упал между 1 и 2 → данные есть, события нет
```

Или наоборот: событие ушло, транзакция откатилась → «фантомное» событие.
Два независимых вызова не могут быть атомарными — нужен outbox.

## Схема

```
┌─ транзакция (одна БД) ─────────────────┐
│ UPDATE orders ...                      │
│ INSERT INTO outbox (topic, key, payload)│
└────────────────────────────────────────┘
              ↓ relay (poll / CDC)
        Kafka / RabbitMQ
              ↓
        consumers (идемпотентные!)
```

## Код

SQL (PostgreSQL):

```sql
CREATE TABLE outbox (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    topic       TEXT        NOT NULL,
    key         TEXT        NOT NULL,          -- ключ партиционирования (сущность)
    payload     JSONB       NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ                    -- NULL = ещё не отправлено
);
CREATE INDEX outbox_unpublished_idx ON outbox (id) WHERE published_at IS NULL;
```

Публикация в той же транзакции (Go, `database/sql`):

```go
func (s *OrderService) Create(ctx context.Context, in CreateOrder) (*Order, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()

	if _, err = tx.ExecContext(ctx,
		`INSERT INTO orders (customer_id, total_cents) VALUES ($1, $2)`,
		in.CustomerID, in.Total); err != nil {
		return nil, err
	}
	payload, err := json.Marshal(map[string]any{"order_id": in.ID, "total_cents": in.Total})
	if err != nil {
		return nil, err
	}
	if _, err = tx.ExecContext(ctx,
		`INSERT INTO outbox (topic, key, payload) VALUES ($1, $2, $3)`,
		"orders.created", strconv.FormatInt(in.ID, 10), payload); err != nil {
		return nil, err // откат: ни заказа, ни события
	}
	return &Order{ID: in.ID}, tx.Commit()
}
```

Relay (polling, упрощённо; в проде — CDC: Debezium/`pgoutput` или pg_outbox-агент):

```go
func (r *Relay) Run(ctx context.Context) error {
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(r.pollInterval):
			if err := r.publishBatch(ctx); err != nil {
				r.log.Error("outbox relay", "err", err) // повторим в следующем цикле
			}
		}
	}
}

// publishBatch: батч → Kafka (acks=all) → в той же БД-транзакции published_at = now().
// Порядок: сначала Kafka, потом отметка. Повторная отправка возможна →
// consumer обязан быть идемпотентным (см. consumer-groups.md).
```

## Правила

1. **Событие пишется в той же транзакции, что и данные** — это и есть суть паттерна.
2. **Ключ события = ключ сущности** — порядок на сущность сохраняется (один партишн).
3. **Consumer идемпотентен**: дубли возможны (at-least-once), защита — idempotency key / upsert.
4. **Отметка `published_at` — после подтверждения брокером** (Kafka: acks=all), не до.
5. **Отравленные сообщения**: N неудачных попыток → отдельная тема/очередь (DLQ) + алерт, не зацикливание.
6. **Мониторинг**: возраст старейшего неопубликованного (lag outbox) — метрика + алерт.

## Pitfalls

- **Relay как «ещё один сервис, который могут забыть»**: без мониторинга lag outbox события «теряются» в таблице.
- **Polling на горячем пути**: интервал = задержка событий; для низких задержек — CDC (pgoutput/Debezium).
- **Большой payload в outbox**: таблица разрастается — храните id сущности, а не весь объект.
- **Удаление опубликованного**: purge по `published_at` старше N дней (N > время жизни реплея), не по `created_at`.
- **Транзакция «длинная»**: outbox-вставка не должна тянуть за собой тяжёлые вычисления.

## Related

- [kafka.md](kafka.md)
- [consumer-groups.md](consumer-groups.md)
- [rabbitmq.md](rabbitmq.md)
- [../../database/snippets/postgres-core.md](../../database/snippets/postgres-core.md)
