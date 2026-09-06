# TypeScript

Целевая версия: **TypeScript 5.9** (fallback: 5.8). Закреплено на 2026-09-06.

## Состав раздела

- `README.md` — этот файл (версия, конвенции)
- `rules.md` — guardrails (запланировано)
- `idioms.md` — идиомы (запланировано)
- `decisions.md` — таблицы решений (запланировано)
- [snippets/](snippets/) — готовые сниппеты
- `patterns/` — паттерны (запланировано)

## Конвенции

- `tsconfig`: `strict: true`, `noUncheckedIndexedAccess: true`, `noImplicitOverride: true`, `exactOptionalPropertyTypes: true` (для новых проектов).
- Модули: ESM (`"type": "module"`), `moduleResolution: "bundler"` или `"nodenext"`.
- Типизация: `unknown` на границе внешних данных (API, env), сужение через type guards.
- Экспорт: named exports; default export — только для классов/компонентов, где это принято.
- `any` — запрещено, кроме обёрток над untyped-зависимостями (с комментарием).

## Инструменты

`tsc --strict`, `eslint` (+ `typescript-eslint`), `prettier`.
