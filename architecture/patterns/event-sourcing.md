---
id: arch-event-sourcing
title: "Архитектура: Event Sourcing"
lang: shared
min_version: "1.21"
category: pattern
tags: [architecture, event-sourcing, audit, projections, advanced, go]
status: experimental
updated: 2026-09-06
---

# Event Sourcing

Храните **события** (факты изменений), а не текущее состояние.
Состояние = fold (сложение) по потоку событий.

**Когда использовать** — полный аудит изменений обязателен (финансы, критичные состояния);
нужно состояние «на момент времени»; инварианты удобно валидировать при append.
**Когда НЕ использовать** — большинство доменов: сложность проецирования, версионирования
событий и снапшотов не окупается (см. [../decisions.md](../decisions.md)).

## Схема

```
Append:  [e1, e2, e3, ...]  (иммутабельный поток)
State:   fold(e1..en) ──▶ Snapshot (опционально, для производительности)
Read:    Projection из событий / снапшотов
```

## Код (Go)

```go
package ledger

import "context"

// События: иммутабельные факты, версионируемые.
type Event struct {
	StreamID string // агрегат (например, ID счёта)
	Version  int64  // порядковый номер в потоке
	Type     string // "account.deposited", "account.withdrawn"
	Payload  []byte // JSON
}

// EventStore: append-only хранилище.
type EventStore interface {
	Append(ctx context.Context, streamID string, expectedVersion int64, events ...Event) error
	ReadStream(ctx context.Context, streamID string, fromVersion int64) ([]Event, error)
}
```

```go
// Fold: состояние из событий.
package ledger

import (
	"encoding/json"
	"fmt"
)

type AccountState struct {
	Balance int64 // в центах
}

func Fold(events []Event) (AccountState, error) {
	var s AccountState
	for _, e := range events {
		switch e.Type {
		case "account.deposited":
			var p struct{ Amount int64 }
			if err := json.Unmarshal(e.Payload, &p); err != nil {
				return AccountState{}, err
			}
			s.Balance += p.Amount
		case "account.withdrawn":
			var p struct{ Amount int64 }
			if err := json.Unmarshal(e.Payload, &p); err != nil {
				return AccountState{}, err
			}
			s.Balance -= p.Amount
		default:
			return AccountState{}, fmt.Errorf("ledger: unknown event %q", e.Type)
		}
	}
	return s, nil
}
```

## Правила

1. **События иммутабельны**: поправка = новое компенсирующее событие.
2. **Версионируйте схему событий** (поле `Version`/`Type`): старые события должны
   оставаться читаемыми (forward compatibility).
3. **Снапшоты** для длинных потоков: состояние на версии N + события после N.
4. **Оптимистичная блокировка**: `expectedVersion` в Append — защита от race.
5. **Чтение — через проекции** (см. [CQRS](cqrs.md)), не «на лету» fold для каждого запроса.

## Антипаттерны

- ❌ «Event sourcing» = просто лог изменений в БД без правил (без версионирования, снапшотов, проекций).
- ❌ Мутабельные события («поправили» payload в БД).
- ❌ Fold на каждом запросе без кэша/снапшотов.

## Related

- [cqrs.md](cqrs.md) — чтение из проекций
- [event-driven.md](event-driven.md) — доставка событий
- [../ddd/tactical/domain-event.md](../ddd/tactical/domain-event.md)
