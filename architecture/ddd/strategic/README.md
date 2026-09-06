# DDD: стратегический дизайн

Границы и язык (уровень DDD ≥ 2).

| Концепция | Суть | Файл |
|---|---|---|
| Bounded Context | граница одной модели и одного языка | [bounded-context.md](bounded-context.md) |
| Ubiquitous Language | язык домена = язык кода | [ubiquitous-language.md](ubiquitous-language.md) |
| Context Mapping | как контексты связаны (ACL, conformist, …) | [context-mapping.md](context-mapping.md) |

## Быстрый выбор

- У одного слова разные значения в разных частях системы → **Bounded Context**.
- Код «переводит» термины домена → **Ubiquitous Language** + глоссарий.
- Интеграция с чужой/legacy-системой → **Context Mapping** (обычно с ACL).
