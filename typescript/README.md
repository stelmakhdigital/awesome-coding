# TypeScript

Целевая версия: **TypeScript 7.0** (fallback: 6.x). Закреплено на 2026-09-06 (сниппеты проверены на tsc 7.0.2).

> 7.x — нативный компилятор (портировка tsc на Go, «tsgo»): значительно быстрее, удалены часть legacy-опций. Сниппеты раздела совместимы с 7.0.

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
