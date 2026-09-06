---
id: shared-mermaid
title: "Shared: Mermaid (диаграммы и схемы в Markdown)"
lang: shared
min_version: null
category: concept
tags: [mermaid, diagrams, flowchart, sequence, c4, documentation]
status: stable
updated: 2026-09-07
---

# Mermaid — диаграммы

**Когда использовать** — потоки, взаимодействия, модели, состояния: в README, `docs/`, ADR.
**Когда НЕ использовать** — объяснение «почему решили так» (это текст ADR), пиксельная графика (это дизайн-инструменты).

## Какая диаграмма для какой задачи

| Задача | Диаграмма | Пример |
|---|---|---|
| Процесс, пайплайн, ветвления | `flowchart` | CI-пайплайн, обработка запроса |
| Взаимодействие сервисов/API, жизненный цикл запроса | `sequenceDiagram` | клиент → API → БД |
| Доменная модель | `classDiagram` | сущности и связи |
| Машина состояний | `stateDiagram-v2` | заказ, платёж |
| Модель данных | `erDiagram` | таблицы и связи |
| Контекст системы (C4) | `C4Context` (mermaid ≥ 10) | система и её окружение |

## Примеры

### flowchart — процесс

```mermaid
flowchart LR
    A[Запрос] --> B{Валиден?}
    B -- да --> C[Обработать]
    B -- нет --> D[400]
    C --> E[Ответ]
```

### sequenceDiagram — взаимодействие

```mermaid
sequenceDiagram
    participant C as Клиент
    participant A as API
    participant D as БД
    C->>A: POST /orders
    A->>D: INSERT order
    D-->>A: ok
    A-->>C: 201 Created
```

### stateDiagram — состояния

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Paid: оплата
    Paid --> Shipped: отправка
    Shipped --> [*]
```

### classDiagram — модель

```mermaid
classDiagram
    class Order {
        +long id
        +string status
        +place()
    }
    class Item {
        +long id
        +long priceCents
    }
    Order "1" --> "*" Item : содержит
```

### erDiagram — данные

```mermaid
erDiagram
    ORDERS ||--o{ ORDER_ITEMS : содержит
    ORDERS {
        bigint id PK
        string status
    }
```

### C4Context — контекст системы (mermaid ≥ 10)

```mermaid
C4Context
    Person(user, "Пользователь")
    System(api, "Order API")
    SystemDb(db, "PostgreSQL")
    Rel(user, api, "HTTPS")
    Rel(api, db, "SQL")
```

## Правила

1. **Одна диаграмма = одна идея**, 5–15 узлов; больше — разбить на несколько.
2. **Подписи — 1–3 слова**; детали — в тексте рядом, не в узлах.
3. **`subgraph`** — группировка (модули, сервисы, зоны).
4. **`direction`** — осознанно: `LR` для потоков, `TB` для иерархий.
5. **`sequenceDiagram`**: `alt/loop/opt` для ветвлений и повторов, `Note` для пояснений.
6. **Диаграмма + 2–3 предложения текста**: что показано, что важно, где детали.
7. **Проверять рендер**: GitHub рендерит mermaid в `.md` — смотреть результат, а не только синтаксис.

## Pitfalls

- **Спецсимволы в подписях ломают синтаксис**: `()`, `[]`, `"` — оборачивать подписи в кавычки: `A["Label (v2)"]`.
- **«Бог-диаграмма» на 40 узлов** — никто её не читает; разбить по идеям.
- **Диаграмма противоречит коду** — то же правило, что для текста: код побеждает, схему чинят в том же коммите.
- **C4 и новые типы** требуют mermaid ≥ 10; старые просмотрщики не отрендерят — не делать док зависимым от одной схемы.
- **Стилизация** (`classDef`, цвета) — зависит от темы рендера, устаревает, усложняет diff — по умолчанию не использовать.

## Правила (жёсткий слой)

- ✅ Диаграмма — для «как взаимодействуют / как течёт»; текст — для «почему решили так».
- ✅ Диаграмма с подписью в тексте (что она показывает).
- ❌ Диаграмма вместо ADR — решение не видно.
- ❌ Стилизация/цвета «для красоты».
- ❌ Диаграмма без рендер-проверки в целевом просмотрщике (GitHub/CI).

## Related

- [documentation.md](documentation.md) — принципы документирования
- [api-design.md](api-design.md) — контракты API
