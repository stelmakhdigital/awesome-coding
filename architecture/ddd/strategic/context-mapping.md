---
id: ddd-context-mapping
title: DDD: Context Mapping
lang: shared
min_version: "n/a"
category: concept
tags: [ddd, context-mapping, integration, acl, boundaries]
status: stable
updated: 2026-09-06
---

# Context Mapping (карта контекстов)

Как bounded contexts связаны между собой: кто upstream, кто downstream,
какой договор о взаимодействии.

**Когда использовать** — уровень DDD ≥ 2, интеграция с чужими системами/контекстами.
**Когда НЕ использовать** — один контекст (границы = весь сервис).

## Типы связей

| Связь | Смысл | Когда |
|---|---|---|
| **Partnership** | Равные партнёры, договариваются вместе | два внутренних контекста одной команды |
| **Shared Kernel** | Общий код под общим владением | действительно общее ядро (см. bounded-context) |
| **Customer/Supplier** | Downstream — «клиент», upstream — «поставщик» | обычный вызов API соседа |
| **Conformist** | Downstream подстраивается под модель upstream | чужой стандарт (платёжный шлюз) |
| **Anti-Corruption Layer (ACL)** | Адаптер переводит чужую модель в свою | legacy/внешняя система с чужим языком |
| **Separate Ways** | Не связаны: не интегрируются | разные продукты |

## Код (Go) — Anti-Corruption Layer

```go
package billing

import "context"

// Ваша доменная модель (упрощённая для примера).
type Charge struct {
	AccountRef  string
	AmountCents int64
	Reason      string
}

type PaymentResult struct {
	Reference string
	Status    string
}

// Модель legacy-шлюза (чужой язык — не проникает в домен).
type legacyCharge struct {
	AccountRef  string
	AmountCents int64
	Reason      string
}

type legacyResponse struct {
	Ref  string
	Code int
}

type LegacyClient interface {
	ChargeLegacy(ctx context.Context, c legacyCharge) (legacyResponse, error)
}

func legacyReason(r string) string { return r }

func mapLegacyStatus(code int) string {
	if code == 0 {
		return "settled"
	}
	return "pending"
}

// ACL: адаптер между вашей моделью и внешней (legacy) системой.
// Домен billing не знает о формате legacy.
type LegacyPaymentGateway struct {
	client LegacyClient // HTTP-клиент к legacy-шлюзу
}

// Charge — ваш доменный контракт.
func (g *LegacyPaymentGateway) Charge(ctx context.Context, c Charge) (PaymentResult, error) {
	// Перевод: ваша модель → чужая модель.
	resp, err := g.client.ChargeLegacy(ctx, legacyCharge{
		AccountRef:  c.AccountRef,
		AmountCents: c.AmountCents,
		Reason:      legacyReason(c.Reason), // маппинг ваших enum'ов в чужие коды
	})
	if err != nil {
		return PaymentResult{}, err
	}
	// Перевод: чужая модель → ваша.
	return PaymentResult{
		Reference: resp.Ref,
		Status:    mapLegacyStatus(resp.Code),
	}, nil
}
```

## Правила

1. **Чужая модель не проникает внутрь**: ACL переводит на границе; домен видит только свои типы.
2. **Conformist — осознанный выбор**: подстраиваться под чужую модель допустимо, если она стабильна и вам нечего предложить взамен.
3. **Карта — документ**: файл `docs/context-map.md` (или диаграмма) с контекстами и связями; обновлять при изменениях.

## Антипаттерны

- ❌ Домен, который парсит JSON чужого legacy-шлюза.
- ❌ «Временный» прямой доступ к чужой БД вместо API/событий.
- ❌ Shared kernel с чужой системой (общий код возможен только внутри владения).

## Related

- [bounded-context.md](bounded-context.md) — что такое контекст
- [../../patterns/microservices.md](../../patterns/microservices.md) — контексы как сервисы
- [../../patterns/event-driven.md](../../patterns/event-driven.md) — асинхронные связи
