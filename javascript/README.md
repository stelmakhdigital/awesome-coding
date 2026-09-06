# JavaScript

Целевой уровень: **ES2024** (fallback: ES2023). Закреплено на 2026-09-06.

## Состав раздела

- `README.md` — этот файл (версия, конвенции)
- `rules.md` — guardrails (запланировано)
- `idioms.md` — идиомы (запланировано)
- `decisions.md` — таблицы решений (запланировано)
- [snippets/](snippets/) — готовые сниппеты
- `patterns/` — паттерны (запланировано)

## Конвенции

- ESM (`import`/`export`), `"type": "module"` в package.json.
- `const` по умолчанию, `let` — при переназначении, `var` — запрещено.
- `async/await` вместо raw-Promise-цепочек; `Promise.all` для независимых, `for..of` + `await` — для зависимых.
- Строгие сравнения (`===`), template literals вместо конкатенации.
- Обработка ошибок: кастомные классы-наследники `Error`; глобальные хендлеры `unhandledRejection`/`uncaughtException`.

## Инструменты

`eslint` (flat config), `prettier`.
