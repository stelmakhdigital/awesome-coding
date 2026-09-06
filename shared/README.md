# Shared — кросс-языковые концепции

Языконезависимые принципы: одинаковые правила для Go, TS/JS, Python, C, Bash, C#, Kotlin, Unity.
Каждая запись: принципы (без языка) → ✅/❌ → идиомы по языкам → пример (Go — референсный язык).

## Записи

| Концепция | Файл |
|---|---|
| Error handling | [error-handling.md](error-handling.md) |
| Concurrency | [concurrency.md](concurrency.md) |
| Security | [security.md](security.md) |
| Testing | [testing.md](testing.md) |
| API design (REST/gRPC/GraphQL) | [api-design.md](api-design.md) |
| Observability | [observability.md](observability.md) |
| Time and dates | [time-and-dates.md](time-and-dates.md) |
| Configuration | [configuration.md](configuration.md) |
| Documentation (ADR, agent-first) | [documentation.md](documentation.md) |
| Mermaid (диаграммы и схемы) | [mermaid.md](mermaid.md) |
| Code Review (правила для агентов) | [code-review.md](code-review.md) |
| Commits (правила коммитинга) | [commits.md](commits.md) |

## Как использовать

1. Принцип есть в `shared/` — применяйте его в любом языке.
2. Языковые детали — в `<lang>/rules.md` и `<lang>/idioms.md`.
3. Конфликт: язык-специфика (`<lang>/`) важнее `shared/`, если это явно указано в записи.

Формат записей — [../docs/FORMAT.md](../docs/FORMAT.md).
