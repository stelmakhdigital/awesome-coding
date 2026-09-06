---
id: ts-decisions
title: "TypeScript Decisions (инструменты, фреймворки)"
lang: typescript
min_version: "7.0"
category: decisions
tags: [decisions, tooling, build, testing, validation, choices]
status: stable
updated: 2026-09-06
---

# TypeScript — таблицы решений

## Сборка и рантайм

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Компилятор | **tsc 7.x** (нативный, Go) | tsc 5.x (JS) | 7.x быстрее в разы; 5.x — если нужна экосистема |
| Bundler (веб) | **Vite** | esbuild напрямую, Rollup | SPA/либraries |
| Node-приложение | tsx / ts-node (dev) + tsc (build) | Bun | — |
| Рантайм | Node 22+ | Deno, Bun | Node — стандарт |

## Типы и валидация

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Валидация внешних данных | **zod** | valibot, yup | zod — стандарт, инференс типов |
| Runtime-типы (multiplatform) | valibot (быстрый) | zod | performance-критично |
| Сериализация | JSON + zod-схемы | class-transformer | — |

## Тестирование

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Unit (Node/веб) | **vitest** | jest | vitest — быстрее, ESM из коробки |
| Unit (только Node) | `node:test` (stdlib) | vitest | без зависимостей |
| E2E (веб) | Playwright | Cypress | — |
| Моки | `vi.fn` / `vi.spyOn` | — | — |

## HTTP и данные

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| HTTP-клиент | **fetch** (stdlib) + AbortController | ky, ofetch | fetch — стандарт |
| HTTP-сервер | **Fastify** | Express, Hono | Fastify — быстрый, типизированный |
| БД (Postgres) | `pg` + zod-схемы | Drizzle, Kysely | Drizzle — типобезопасный SQL |
| Очереди | BullMQ (Redis) | — | — |

## Стиль и качество

| Задача | Рекомендация | Альтернатива |
|---|---|---|
| Линтер | **eslint** + typescript-eslint (flat config) | biome (быстрее, меньше правил) |
| Форматтер | prettier | biome |
| Аналитика | tsc (строгий режим) | — |

## Related

- [rules.md](rules.md)
- [shared/api-design.md](../shared/api-design.md)
