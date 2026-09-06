---
id: csharp-state-machine
title: "C#: State Machine (явные переходы)"
lang: csharp
min_version: "10"
category: pattern
tags: [pattern, state-machine, domain, invariants]
status: stable
updated: 2026-09-06
---

# State Machine (C#)

Явные состояния и разрешённые переходы: нет «магических» статусов,
невалидный переход — исключение в момент попытки.

**Когда использовать** — сущность с жизненным циклом (заказ, платёж, заявка),
где переходов больше 3 и они неочевидны.
**Когда НЕ использовать** — 2–3 состояния (enum + if достаточно);
сложные графы с условиями → библиотека (`Stateless`).

## Код

```csharp
using System.Collections.Generic;

public enum PaymentState
{
    Pending,
    Authorized,
    Settled,
    Failed,
    Refunded,
}

// Таблица переходов: весь граф жизненного цикла в одном месте.
public sealed class PaymentStateMachine
{
    private static readonly Dictionary<PaymentState, HashSet<PaymentState>> Transitions = new()
    {
        [PaymentState.Pending] = [PaymentState.Authorized, PaymentState.Failed],
        [PaymentState.Authorized] = [PaymentState.Settled, PaymentState.Failed],
        [PaymentState.Settled] = [PaymentState.Refunded],
        [PaymentState.Failed] = [],
        [PaymentState.Refunded] = [],
    };

    public PaymentState State { get; private set; } = PaymentState.Pending;

    public void TransitionTo(PaymentState next)
    {
        if (!Transitions[State].Contains(next))
        {
            throw new InvalidStateTransitionException(State, next);
        }
        State = next;
    }

    public bool CanTransitionTo(PaymentState next) => Transitions[State].Contains(next);
}

public sealed class InvalidStateTransitionException(PaymentState from, PaymentState to)
    : InvalidOperationException($"Payment: cannot transition from {from} to {to}");
```

## Правила

1. **Граф переходов — данные** (таблица), не размазанные `if` по методам.
2. **Состояние приватное**: меняется только через `TransitionTo`.
3. **`CanTransitionTo`** — для UI (кнопка «Оплатить» активна только при `Pending`).
4. **События на переходы** (опционально): `event Action<PaymentState, PaymentState>? Transitioned`
   — для доменных событий (см. [architecture/ddd/tactical/domain-event.md](../../architecture/ddd/tactical/domain-event.md)).

## Антипаттерны

- ❌ Переходы, проверяемые в сервисах («сначала проверь статус, потом меняй»).
- ❌ Статус, который можно присвоить напрямую (`payment.Status = X`).
- ❌ Граф с «переходом в любое состояние» — это не state machine.

## Related

- [architecture/ddd/tactical/entity.md](../../architecture/ddd/tactical/entity.md)
- [testing.md](../snippets/testing.md) — как тестировать переходы
