# DDD: тактические паттерны

Составляющие доменной модели (уровень DDD ≥ 1). Референсные реализации — на Go.

| Паттерн | Суть | Файл |
|---|---|---|
| Entity | идентичность первична, состояние вторично | [entity.md](entity.md) |
| Value Object | равенство по значению, иммутабельность | [value-object.md](value-object.md) |
| Aggregate | граница согласованности, инварианты на корне | [aggregate.md](aggregate.md) |
| Domain Service | поведение, не принадлежащее одному агрегату | [domain-service.md](domain-service.md) |
| Domain Event | факт в прошедшем времени | [domain-event.md](domain-event.md) |
| Repository | на агрегат, не на таблицу | [repository.md](repository.md) |

## Быстрый выбор

- Объект с жизненным циклом и ID → **Entity**.
- Неизменяемое описание (деньги, адрес) → **Value Object**.
- Несколько сущностей с общими инвариантами → **Aggregate**.
- Операция над двумя агрегатами → **Domain Service**.
- Реакция другого модуля на факт → **Domain Event**.
- Хранение агрегата → **Repository**.
