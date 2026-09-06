# JavaScript

Целевой уровень: **ES2025** (fallback: ES2024). Закреплено на 2026-09-06.

## Состав раздела

- `README.md` — этот файл (версия, конвенции)
- [rules.md](rules.md) — guardrails (✅/❌)
- [idioms.md](idioms.md) — идиомы (ES2025: iterators, groupBy, withResolvers)
- [decisions.md](decisions.md) — таблицы решений (рантайм, тесты, HTTP)
- [snippets/](snippets/) — готовые сниппеты (error-handling, testing, json, async)

## Конвенции

- ESM (`import`/`export`), `"type": "module"` в package.json.
- `const` по умолчанию, `let` — при переназначении, `var` — запрещено.
- `async/await` вместо raw-Promise-цепочек; `Promise.all` для независимых, `for..of` + `await` — для зависимых.
- Строгие сравнения (`===`), template literals вместо конкатенации.
- Обработка ошибок: кастомные классы-наследники `Error`; глобальные хендлеры `unhandledRejection`/`uncaughtException`.

## Инструменты

`eslint` (flat config), `prettier`.
