# awesome-coding

Библиотека сниппетов, паттернов и правил для **кодинг-агентов** (и людей).
Структурирована по языкам: **Go, TypeScript, JavaScript, Python, C, Bash, C#** + раздел **Unity** (кроссплатформенные и Android-игры).

## Почему agent-first

Основной потребитель репозитория — LLM-агент, а не человек. Отсюда дизайн:

- **Предсказуемая структура и имена** — агент читает только нужное, а не всё подряд.
- **YAML frontmatter** у каждой записи — метаданные для поиска (теги, версия, статус).
- **Высокая плотность сигнала** — «когда использовать / когда нет», Do/Don't-пары, pitfalls.
- **Закреплённые версии языков** — агент не пишет устаревшие идиомы.
- **`AGENTS.md`** — короткий «роутер» для агента, а не дамп контента.

## Структура

```
awesome-coding/
├── AGENTS.md                  # точка входа для агента (роутер)
├── docs/
│   ├── FORMAT.md              # спецификация формата записей
│   └── CONTRIBUTING.md
├── index/
│   └── manifest.yaml          # машиночитаемый каталог всех записей
├── go/                        # языковой раздел (эталонный)
│   ├── README.md              # версия, конвенции, quick-reference
│   ├── rules.md               # guardrails: do/don't (✅/❌)
│   ├── idioms.md              # идиоматичный Go
│   ├── decisions.md           # таблицы решений: что выбрать и когда
│   ├── snippets/              # готовые сниппеты
│   └── patterns/              # архитектурные/дизайн-паттерны
├── architecture/              # языконезависимая архитектура и DDD
│   ├── decisions.md           # какой уровень DDD / какая архитектура для проекта
│   ├── ddd/                   # tactical (entity, VO, aggregate, …) + strategic (bounded contexts)
│   └── patterns/              # layered, hexagonal, modular monolith, microservices, CQRS, ES, event-driven
├── typescript/                # (аналогичная структура)
├── javascript/
├── python/
├── c/
├── bash/
├── csharp/                    # .NET 10 / C# 14
├── unity/                     # Unity 6.3 LTS: кроссплатформа + Android
└── shared/                    # кросс-языковые концепции
```

## Версии языков (закреплено и проверено на 2026-09-06)

| Язык | Версия | Fallback |
|---|---|---|
| Go | 1.27 | 1.26 |
| TypeScript | 7.0 | 6.x |
| JavaScript | ES2025 | ES2024 |
| Python | 3.14 | 3.13 |
| C | C23 (ISO 9899:2024) | C17 |
| Bash | 5.3 | 5.2 |
| C# | .NET 10 (LTS) / C# 14 | .NET 9 / C# 13 |
| Unity | 6.3 LTS (6000.3.x) | 6.0 LTS |

## Для агентов

Начните с [AGENTS.md](AGENTS.md).

## Для контрибьюторов

- Формат записей: [docs/FORMAT.md](docs/FORMAT.md)
- Правила контрибьюции: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)

## Статус разделов

| Раздел | Статус |
|---|---|
| `go/` | ядро: snippets, patterns, rules, idioms, decisions |
| `architecture/` | полный: DDD (tactical + strategic) + 7 архитектурных паттернов |
| `csharp/` | полный: snippets, patterns, rules, idioms, decisions (.NET 10 / C# 14) |
| `unity/` | полный: snippets, patterns, rules, idioms, decisions (6.3 LTS, Android) |
| `typescript/`, `javascript/`, `python/`, `c/`, `bash/` | каркас + эталонный сниппет |
| `shared/` | запланировано |

## License

[MIT](LICENSE)
