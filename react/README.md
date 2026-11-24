# React

Целевые версии: **React 19.3** (fallback: 18.3), **Vite 8.3** (fallback: 6.x), **Vitest 5.1** (fallback: 3.x), **Testing Library 16.3**. Закреплено на 2026-11-25 (сниппеты проверены на tsc 7.0.2 + react 19.3.1).

> 19-я линия сломала много тихого: удалены `defaultProps` у функций, string refs, `ReactDOM.render`; глобального пространства имён `JSX` в типах больше нет; `useRef` требует начальный аргумент. Vite 8 заменил бандлер (Rolldown вместо esbuild + Rollup), Vitest 5 поднял `clearMocks` по умолчанию. Раздел описывает текущее состояние, fallback-строки — про то, что лежит в живых проектах.

## Состав раздела

- `README.md` — этот файл (версии, конвенции)
- [rules.md](rules.md) — guardrails (✅/❌)
- [decisions.md](decisions.md) — таблицы решений (состояние, данные, формы, слои тестов, миграция сборки)
- [snippets/](snippets/) — компоненты, состояние, эффекты, тесты, Vite, формы, тяжёлые виджеты, проверка вёрстки
- [patterns/feature-structure.md](patterns/feature-structure.md) — структура проекта по фичам

Идиомы языка — в [../typescript/](../typescript/), оформление коммитов — в [../shared/commits.md](../shared/commits.md). Дублировать их здесь смысла нет: React меняет не синтаксис, а правила «где держать состояние и когда эффект законен».

## Конвенции

- Только функциональные компоненты. Классовые — легаси: `ReactDOM.render` и `react-dom/test-utils` удалены в 19, поддерживать их alongside дороже.
- Файлы компонентов — `PascalCase.tsx`, один экспорт на файл; хуки — `useCamelCase.ts`.
- Пропсы типизируются явно (`type Props = {...}`), `defaultProps` для функций удалён — значения по умолчанию в деструктуризации.
- Типы JSX берутся из `react`: `import type { ReactElement, JSX } from "react"`. Глобального `JSX` нет.
- `strict: true` в `tsconfig` и `--jsx react-jsx`: автоматическая JSX-фабрика, `import React from "react"` не нужен.
- Стилизация: CSS Modules или one-file-per-component CSS. Инлайн-стили — только вычисляемые значения (позиция, ширина прогресса).
- Тесты — по поведению через доступные роли (`getByRole`), не через классы и `data-testid`.

## Инструменты

`tsc --noEmit --strict` (7.0), `vite build` (8.3, Rolldown), `vitest run` (5.1, jsdom), `@testing-library/react` (16.3) + `user-event`, `eslint` + `eslint-plugin-react-hooks`.

Прогон код-блоков раздела: `make verify` (раннер `tsx`: `tsc --strict --lib es2024,dom --jsx react-jsx`, см. [../docs/FORMAT.md](../docs/FORMAT.md)).
