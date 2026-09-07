---
id: ts-rules
title: "TypeScript Rules"
lang: typescript
min_version: "7.0"
category: rule-set
tags: [rules, guardrails, strict, types, style]
status: stable
updated: 2026-09-07
---

# TypeScript Rules — обязательные правила

## Типизация

- ✅ `strict: true` + `noUncheckedIndexedAccess` + `noImplicitOverride` + `exactOptionalPropertyTypes` (новые проекты).
- ✅ `unknown` на границе внешних данных (API, env, JSON) — сужение через type guards / zod.
- ❌ `any` — запрещено, кроме обёрток над untyped-зависимостями (с комментарием).
- ❌ `as`-касты «чтобы про компилилось» — только с комментарием и причиной.
- ✅ `satisfies` — проверка типа без потери инференса.
- ✅ `const`-ассерты (`as const`) для литеральных типов.

## Код

- ✅ ESM (`"type": "module"`), `moduleResolution: "bundler"` или `"nodenext"`.
- ✅ Named exports; default export — только для классов/компонентов.
- ✅ `readonly` для коллекций, которые не мутатируются.
- ✅ `void`/`Promise<void>` для функций без результата (не `undefined`).
- ✅ `import type` для импорта только типов.
- ❌ Мутация аргументов-коллекций (передавайте копии или `readonly`).

## Именование

- ✅ Переменные, функции, методы: `camelCase` (`userName`, `fetchItems`).
- ✅ Типы, интерфейсы, классы, enum'ы: `PascalCase` (`UserService`, `HttpError`).
- ✅ Константы модуля: `UPPER_SNAKE_CASE` (`MAX_RETRIES`); члены enum — `PascalCase`.
- ✅ Файлы: `kebab-case` (`http-client.ts`); один модуль — один файл.
- ✅ Булевы: префикс `is`/`has`/`should`/`can` (`isValid`, `hasPermission`).
- ❌ Нет ведущего подчёркивания для «приватного» — `#field`/модификатор `private`.
- ❌ Нет венгерской нотации (`strName`, `iCount`) и аббревиатур, требующих словаря.

## Асинхронность

- ✅ `async/await` + `AbortController` для отмены.
- ✅ `Promise.all` для независимых, `for..of` + await для зависимых.
- ❌ Callbacks там, где есть корутины/промисы.
- ✅ Таймауты на всех внешних вызовах (см. [snippets/async.md](snippets/async.md)).

## Ошибки

- ✅ Кастомные классы-ошибки с `code` (машиночитаемый) + `message` (человекочитаемый).
- ✅ `try/catch` — на границах (HTTP-хендлер, CLI), не «на каждый вызов».
- ❌ Пустой `catch {}`.
- ✅ Глобальные хендлеры: `process.on("unhandledRejection")` — лог + осознанный exit.

## Related

- [idioms.md](idioms.md) — идиомы
- [decisions.md](decisions.md) — выбор инструментов
- [shared/error-handling.md](../shared/error-handling.md)
