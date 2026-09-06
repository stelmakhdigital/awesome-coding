---
id: js-decisions
title: "JavaScript Decisions (рантайм, тесты, инструменты)"
lang: javascript
min_version: "ES2025"
category: decisions
tags: [decisions, runtime, node, testing, tooling, choices]
status: stable
updated: 2026-09-06
---

# JavaScript — таблицы решений

## Рантайм

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Сервер/CLI | **Node 22+ (LTS)** | Deno, Bun | Node — стандарт, экосистема |
| Edge/worker | Bun / Deno | — | холодный старт |
| Браузер | нативный ES2025 | — | без бандлера (модули) |

## Тестирование

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Unit (Node) | **node:test** (stdlib) | vitest, jest | без зависимостей |
| Unit (веб/TS) | vitest | jest | TS из коробки |
| E2E (веб) | Playwright | Cypress | — |
| Моки | `node:test/mock` | sinon | — |

## HTTP и данные

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| HTTP-клиент | **fetch** (stdlib) | undici (Node-опции) | — |
| HTTP-сервер | **Fastify** | Express, Hono | Fastify — быстрый |
| БД (Postgres) | `pg` | Drizzle (типизация) | — |
| Очереди | BullMQ (Redis) | — | — |

## Качество

| Задача | Рекомендация | Альтернатива |
|---|---|---|
| Линтер | **eslint** (flat config) | biome |
| Форматтер | prettier | biome |
| Пакетный менеджер | **pnpm** | npm, bun |

## TypeScript или JavaScript?

| Критерий | JS | TS |
|---|---|---|
| Скрипты, CLI, прототипы | ✅ | — |
| Сервисы, команды > 1 человека | — | ✅ |
| Публичные API/библиотеки | — | ✅ (типы = контракт) |

**Правило**: для нового серверного кода — TS (см. [../typescript/](../typescript/)); JS — для скриптов и tooling.

## Related

- [rules.md](rules.md)
- [../typescript/decisions.md](../typescript/decisions.md)
