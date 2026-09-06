---
id: ddd-domain-service
title: DDD: Domain Service
lang: shared
min_version: "1.21"
category: pattern
tags: [ddd, domain-service, service, go]
status: stable
updated: 2026-09-06
---

# Domain Service (доменный сервис)

Безсостоятельная операция, которая **не принадлежит ни одной сущности/агрегату**:
перевод между счётами, расчёт налога по нескольким позициям, матчмейкинг.

**Когда использовать** — поведение, которое логически доменное, но не влезает
в один агрегат (операция над двумя и более агрегатами).
**Когда НЕ использовать** — оркестрация, транзакции, I/O, «все действия приложения»
→ это application service (прикладной слой), а не доменный.

## Код (Go)

```go
package transfer

import (
	"context"
	"errors"

	"example.com/bank/bank"
	"example.com/bank/money"
)

// Domain service: безсостоянен, работает с агрегатами.
// Инварианты по-прежнему проверяются на корнях (Withdraw/Deposit).
type Service struct {
	accounts bank.AccountRepository
}

func NewService(accounts bank.AccountRepository) *Service {
	return &Service{accounts: accounts}
}

// Перевод: операция, которую не может выполнить ни один из счётов в одиночку.
func (s *Service) Execute(ctx context.Context, from, to bank.AccountID, amount money.Money) error {
	if from == to {
		return errors.New("transfer: same account")
	}
	src, err := s.accounts.Get(ctx, from)
	if err != nil {
		return err
	}
	dst, err := s.accounts.Get(ctx, to)
	if err != nil {
		return err
	}
	// Инвариант проверяется на корне src.
	if err := src.Withdraw(amount); err != nil {
		return err
	}
	if err := dst.Deposit(amount); err != nil {
		return err
	}
	// Сохранение обоих агрегатов — ответственность слоя выше (транзакция).
	if err := s.accounts.Save(ctx, src); err != nil {
		return err
	}
	return s.accounts.Save(ctx, dst)
}
```

## Правила

- **Безсостоянен**: все данные приходят из аргументов и агрегатов; нет полей-накопителей.
- **Не дублирует поведение модели**: если логика «проверяет баланс» — значит,
  `Withdraw` на корне сделан неправильно.
- **Не оркестрирует прикладные сценарии**: отправка email, логирование, HTTP — не сюда.

## Граница с application service

| Domain service | Application service |
|---|---|
| Доменные правила над агрегатами | Оркестрация use case'а |
| Без I/O | Транзакции, I/O, события наружу |
| Зависит от домена | Зависит от домена + инфраструктуры |

## Антипаттерны

- ❌ «God service», в который вынесено всё поведение (тогда у модели нет поведения — anemic model).
- ❌ Доменный сервис с полями-состоянием (каштан из «service locator»).
- ❌ Domain service, который сам открывает БД/HTTP.

## Related

- [aggregate.md](aggregate.md) — инварианты на корне
- [../README.md — золотые правила DDD](../README.md)
