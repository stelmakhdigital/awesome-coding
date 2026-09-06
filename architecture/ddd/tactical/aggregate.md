---
id: ddd-aggregate
title: "DDD: Aggregate"
lang: shared
min_version: "1.21"
category: pattern
tags: [ddd, aggregate, invariants, consistency, go]
status: stable
updated: 2026-09-06
---

# Aggregate (агрегат)

Агрегат — **граница согласованности**: кластер сущностей, которые изменяются
только как единое целое. Внешний мир знает только **корень** (root); внутренние
объекты недоступны напрямую.

**Когда использовать** — несколько сущностей, между которыми есть инварианты
(счёт + операции по счёту; заказ + позиции заказа).
**Когда НЕ использовать** — одиночная сущность (просто [entity](entity.md));
«весь домен в одном агрегате» (антипаттерн, см. ниже).

## Код (Go)

```go
package bank

import (
	"errors"
	"time"

	"example.com/bank/money"
)

var ErrInsufficientFunds = errors.New("bank: insufficient funds")

type AccountID string

// Aggregate root: защищает инварианты.
// Внутренние объекты (ledger) неэкспортированы — доступ только через root.
type Account struct {
	id      AccountID
	balance money.Money
	ledger  []Entry // internal: наружу не отдаём
}

type Entry struct {
	Amount money.Money
	At     time.Time
}

func NewAccount(id AccountID, initial money.Money) (*Account, error) {
	if initial.Less(money.Money{}) {
		return nil, errors.New("bank: negative initial balance")
	}
	return &Account{id: id, balance: initial}, nil
}

func (a *Account) ID() AccountID {
	return a.id
}

func (a *Account) Balance() money.Money {
	return a.balance
}

// Инвариант: баланс не уходит в минус. Проверяется на корне.
func (a *Account) Withdraw(amount money.Money) error {
	if a.balance.Less(amount) {
		return ErrInsufficientFunds
	}
	b, _ := a.balance.Sub(amount)
	a.balance = b
	a.ledger = append(a.ledger, Entry{Amount: amount, At: time.Now()})
	return nil
}

func (a *Account) Deposit(amount money.Money) error {
	b, err := a.balance.Add(amount)
	if err != nil {
		return err
	}
	a.balance = b
	a.ledger = append(a.ledger, Entry{Amount: amount, At: time.Now()})
	return nil
}
```

## Правила

1. **Один корень** на агрегат; внутренние объекты — только через корень.
2. **Инварианты — на корне**: никакая внешняя операция не может нарушить их.
3. **Ссылки на другие агрегаты — по ID**, а не по указателю (иначе границы сливаются).
4. **Агрегат мал**: 1–5 объектов. Если инвариант «не влезает» — границы выбраны неверно.
5. **Транзакция = один агрегат**: не держите транзакцию, охватывающую несколько агрегатов.

## Антипаттерны

- ❌ **God-агрегат**: весь домен в одном корне (Order + Customer + Payment + Inventory).
- ❌ Инварианты проверяются **снаружи** агрегата (в сервисе): «сначала проверь, потом поменяй».
- ❌ Экспортированные внутренние объекты (`Account.Ledger []Entry`) — инварианты ломаются.
- ❌ Глубокие графы объектов внутри агрегата — трудно сериализовать и тестировать.

## Related

- [entity.md](entity.md) — сущность внутри агрегата
- [value-object.md](value-object.md) — VO внутри агрегата
- [repository.md](repository.md) — repository на агрегат
- [domain-service.md](domain-service.md) — операция над несколькими агрегатами
