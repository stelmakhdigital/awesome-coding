---
id: shared-api-design
title: "Shared: API design (REST/gRPC/GraphQL контракты)"
lang: shared
min_version: null
category: concept
tags: [api, rest, grpc, graphql, contracts, http]
status: stable
updated: 2026-09-06
---

# API design — принципы

**Когда использовать** — проектирование/изменение публичных API (внутренние сервисы, HTTP-эндпоинты, контракты).
**Когда НЕ использовать** — приватные функции внутри модуля.

## Выбор протокола

| Задача | Рекомендация | Когда |
|---|---|---|
| Публичный HTTP API, разные клиенты | **REST** | браузеры, мобильные, интеграции |
| Внутренние сервисы, строгие контракты | **gRPC** | microservices, высокая частота |
| Клиент запрашивает «ровно то, что нужно» | **GraphQL** | мобильные/веб с разнородными экранами |
| События/стримы | gRPC streaming / SSE / WebSockets | live-данные |

## REST: правила

1. **Ресурсы — существительные**: `/orders/{id}`, не `/getOrder`.
2. **Глагол — в HTTP-методе**: `GET/POST/PUT/PATCH/DELETE`; `POST` — создание, `PUT` — замена, `PATCH` — частичное.
3. **Коды ответов — по смыслу**: `200/201/204`, `400` (валидация), `401` (auth), `403` (authz), `404`, `409` (конфликт), `422` (семантика), `429` (rate limit), `500` (сбой сервера).
4. **Ошибки — структурированные**: `{ "error": { "code": "ORDER_NOT_FOUND", "message": "..." } }` — стабильные коды для клиентов.
5. **Пагинация**: cursor-based для больших коллекций (`?cursor=...&limit=...`), offset — только для UI.
6. **Идемпотентность**: `PUT`/`DELETE` — идемпотентны; `POST` — с `Idempotency-Key` для критичных операций.
7. **Версионирование**: `/v1/` в URL; breaking changes — только новая версия; deprecation — заголовки + срок.
8. **Контракт — OpenAPI (Swagger)**: генерируется из кода или пишется первым (contract-first).

## gRPC: правила

1. **Protobuf-контракт** — источник истины; коды — генерируются.
2. **Статусы — `google.rpc.Status`** (code + message + details), не free-form.
3. **Service = доменная граница** (bounded context), не «один service на всё».
4. **Streaming**: server-streaming для «потока событий», bidirectional — для чатов.
5. **Версионирование**: пакет protobuf (`v2`), не переиспользуйте номера полей.

## GraphQL: правила

1. **Schema-first**: схема — контракт; резолверы — реализация.
2. **N+1 — главный враг**: DataLoader/батчинг обязателен для списков.
3. **Ограничения**: depth limit, query cost, rate limit — на уровне сервера.
4. **Мутирования — idempotency key** (для `mutation`).
5. **Не делайте «GraphQL на всё»**: отчёты/выгрузки — REST (cursor-пагинация).

## Контракты и breaking changes

- ✅ Контракт (OpenAPI/protobuf/schema) — в репо, ревьюится как код.
- ✅ Добавление полей/опциональных параметров — не breaking.
- ❌ Удаление/переименование полей, смена типов — breaking: новая версия + миграция.
- ✅ Deprecation: заголовок `Deprecation`/`Sunset`, срок, альтернатива.
- ✅ Тесты контракта (contract tests): клиент и сервер проверяют один контракт.

## Related

- [go/snippets/http-server.md](../go/snippets/http-server.md) — REST-сервер (Go)
- [typescript/snippets/http-client.md](../typescript/snippets/http-client.md) — HTTP-клиент
- [cicd/](../cicd/) — как деплоить API
