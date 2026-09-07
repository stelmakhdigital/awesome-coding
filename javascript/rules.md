---
id: js-rules
title: "JavaScript Rules"
lang: javascript
min_version: "ES2025"
category: rule-set
tags: [rules, guardrails, esm, async, style]
status: stable
updated: 2026-09-07
---

# JavaScript Rules — обязательные правила

## Код

- ✅ ESM (`"type": "module"`) — по умолчанию; CJS — только legacy.
- ✅ `const` по умолчанию; `let` — когда нужна переопределение; ❌ `var`.
- ✅ Строгие сравнения (`===`/`!==`); `==` — только `== null` (идиома null-check).
- ✅ `async/await` — не промисы с цепочками `.then` (кроме коротких цепочек).
- ✅ `import`/`export` — named exports; default — только для классов/компонентов.
- ✅ `#private` поля для приватного состояния классов.
- ❌ Мутация аргументов-коллекций.
- ❌ Глобальные переменные «на уровне модуля» для состояния — явный объект/класс.

## Именование

- ✅ Переменные, функции: `camelCase`; классы: `PascalCase`.
- ✅ Константы модуля: `UPPER_SNAKE_CASE` (`MAX_RETRIES`).
- ✅ Файлы: `kebab-case` (`http-client.js`); один модуль — один файл.
- ✅ Булевы: префикс `is`/`has`/`should`/`can`.
- ❌ Нет венгерской нотации и заумных аббревиатур; «приватное» — `#field`, не `_field`.

## Асинхронность

- ✅ `AbortController` для отмены; таймауты на всех внешних вызовах.
- ✅ `Promise.all` — независимые; `for..of` + await — зависимые; лимит — для больших наборов.
- ❌ `setImmediate`/`setTimeout` как синхронизация (race condition).
- ✅ `queueMicrotask`/`Promise.resolve().then` — для микрозаданий.

## Ошибки

- ✅ Кастомные классы-ошибки с `code` (машиночитаемый) + `message`.
- ✅ `try/catch` — на границах (HTTP-хендлер, CLI), не «на каждый вызов».
- ✅ Глобальные хендлеры: `process.on("unhandledRejection")`, `process.on("uncaughtException")` — лог + осознанный exit.
- ❌ Пустой `catch {}`.

## Node-специфика

- ✅ `node:`-префикс для встроенных модулей (`node:fs`, `node:path`).
- ✅ `fs/promises` (async), не callback-`fs`.
- ✅ Путь — `path.join`/`path.resolve`, не конкатенация строк.
- ✅ Секреты — из env (`process.env`), не в коде.

## Безопасность

- ❌ `eval`/`new Function`/`vm` с внешним вводом (code injection).
- ✅ DOM: `textContent`/`createElement` (не `innerHTML` с внешними данными) — XSS.
- ✅ Node: `execFile`/`spawn` с массивом аргументов (не `exec` со строкой, не `shell: true`).
- ✅ Крипто — `node:crypto` (не `Math.random` для токенов/солей).
- ❌ Секреты в клиентском коде — бандл публичный; только через API-слой.

## Related

- [idioms.md](idioms.md) — идиомы
- [decisions.md](decisions.md) — выбор инструментов
- [shared/error-handling.md](../shared/error-handling.md)
