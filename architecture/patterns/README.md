# Архитектурные паттерны

| Паттерн | Суть | Статус | Файл |
|---|---|---|---|
| Layered | handlers → application → domain → infra | stable | [layered.md](layered.md) |
| Hexagonal | ports & adapters, ядро без зависимостей | stable | [hexagonal.md](hexagonal.md) |
| Modular Monolith | один deployable, жёсткие модульные границы | stable | [modular-monolith.md](modular-monolith.md) |
| Microservices | отдельные deployable по bounded contexts | stable | [microservices.md](microservices.md) |
| CQRS | разделение моделей чтения и записи | experimental | [cqrs.md](cqrs.md) |
| Event Sourcing | состояние = fold по событиям | experimental | [event-sourcing.md](event-sourcing.md) |
| Event-Driven | асинхронное взаимодействие через события | experimental | [event-driven.md](event-driven.md) |

## Быстрый выбор

- Простой сервис, один интерфейс → **Layered**.
- Несколько интерфейсов / тестируемость → **Hexagonal**.
- Несколько команд/доменов, один deployable → **Modular Monolith**.
- Независимое масштабирование/деплой → **Microservices** (после монолита).
- Асимметрия чтения/записи → **CQRS**.
- Аудит истории состояний → **Event Sourcing**.
- Слабая связанность, интеграции → **Event-Driven** (outbox).
