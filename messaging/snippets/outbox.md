---
id: messaging-outbox
title: "Outbox: события из транзакции без потери и дублей"
lang: messaging
min_version: "4.3"
category: pattern
tags: [outbox, events, transaction, reliability, cdc, kafka]
status: stable
updated: 2026-11-24
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
// Package outbox — событие пишется в той же транзакции, что и данные.
package outbox

import (
	"context"
	"database/sql"
	"encoding/json"
	"strconv"
)

// OrderService — доступ к БД: она источник истины и для данных, и для outbox.
type OrderService struct{ db *sql.DB }

// CreateOrder — вход; Order — то, что вернём вызывающему.
type (
	CreateOrder struct {
		CustomerID string
		Total      int64
	}
	Order struct {
		ID int64
	}
)

// Create заказывает и кладёт событие в outbox одной транзакцией.
func (s *OrderService) Create(ctx context.Context, in CreateOrder) (*Order, error) {
	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback() // после успешного Commit — no-op

	var id int64
	if err := tx.QueryRowContext(ctx,
		`INSERT INTO orders (customer_id, total_cents) VALUES ($1, $2) RETURNING id`,
		in.CustomerID, in.Total).Scan(&id); err != nil {
		return nil, err
	}

	payload, err := json.Marshal(map[string]any{"order_id": id, "total_cents": in.Total})
	if err != nil {
		return nil, err
	}
	if _, err = tx.ExecContext(ctx,
		`INSERT INTO outbox (topic, key, payload) VALUES ($1, $2, $3)`,
		"orders.created", strconv.FormatInt(id, 10), payload); err != nil {
		return nil, err // откат: ни заказа, ни события
	}

	if err := tx.Commit(); err != nil {
		return nil, err
	}
	return &Order{ID: id}, nil
}
```

Relay (polling, упрощённо; в проде — CDC: Debezium/`pgoutput` или pg_outbox-агент):

```go
// Package relay — отправляет outbox в брокер и только потом отмечает строки.
package relay

import (
	"context"
	"database/sql"
	"fmt"
	"log/slog"
	"time"
)

// Relay — опрос outbox. В проде чаще CDC (Debezium / pgoutput), но polling проще
// и не требует прав на WAL. publish — отправка в брокер (injected: Kafka, RabbitMQ).
type Relay struct {
	db           *sql.DB
	publish      func(ctx context.Context, topic, key string, payload []byte) error
	pollInterval time.Duration
	log          *slog.Logger
}

// Run крутит publishBatch до отмены ctx. Ошибка батча не останавливает цикл.
func (r *Relay) Run(ctx context.Context) error {
	t := time.NewTicker(r.pollInterval)
	defer t.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-t.C:
			if err := r.publishBatch(ctx); err != nil {
				r.log.Error("outbox relay", "err", err) // повторим в следующем цикле
			}
		}
	}
}

type msg struct {
	id      int64
	topic   string
	key     string
	payload []byte
}

// publishBatch: выбрать батч с блокировкой строк, отправить, отметить, закоммитить.
// SKIP LOCKED — несколько релиев не дерутся за одни и те же строки.
func (r *Relay) publishBatch(ctx context.Context) error {
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer tx.Rollback()

	rows, err := tx.QueryContext(ctx,
		`SELECT id, topic, key, payload
		   FROM outbox
		  WHERE published_at IS NULL
		  ORDER BY id
		     LIMIT 100
		       FOR UPDATE SKIP LOCKED`)
	if err != nil {
		return fmt.Errorf("select outbox: %w", err)
	}

	var batch []msg
	for rows.Next() {
		var m msg
		if err := rows.Scan(&m.id, &m.topic, &m.key, &m.payload); err != nil {
			rows.Close()
			return fmt.Errorf("scan outbox: %w", err)
		}
		batch = append(batch, m)
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return fmt.Errorf("rows outbox: %w", err)
	}
	rows.Close()

	for _, m := range batch {
		// Порядок: сначала брокер, потом отметка. Падение между ними = повторная
		// отправка в следующем цикле, поэтому потребитель идемпотентен.
		if err := r.publish(ctx, m.topic, m.key, m.payload); err != nil {
			return fmt.Errorf("publish %s/%d: %w", m.topic, m.id, err)
		}
		if _, err := tx.ExecContext(ctx,
			`UPDATE outbox SET published_at = now() WHERE id = $1`, m.id); err != nil {
			return fmt.Errorf("mark %d: %w", m.id, err)
		}
	}
	return tx.Commit()
}
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
