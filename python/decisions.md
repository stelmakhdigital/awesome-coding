---
id: py-decisions
title: "Python Decisions (библиотеки, фреймворки)"
lang: python
min_version: "3.14"
category: decisions
tags: [decisions, libraries, http, testing, web, choices]
status: stable
updated: 2026-09-06
---

# Python — таблицы решений

## Web-фреймворки

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| API-сервис | **FastAPI** | Flask, Litestar | FastAPI — async + типы из коробки |
| Простой сервис | Flask | — | минимум магии |
| Высоконагруженный | Litestar / FastAPI | — | — |

## HTTP-клиент

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Async + sync | **httpx** | aiohttp | httpx — API как requests, async из коробки |
| Только sync | requests | httpx | legacy-код |
| Streaming | httpx (`stream=True`) | — | — |

## Данные

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Postgres (async) | **psycopg 3** | asyncpg | psycopg 3 — sync+async, типизация |
| ORM | SQLAlchemy 2 (async) | — | DDD/сложные модели |
| Валидация/схемы | **pydantic v2** | — | DTO, конфиг, API |
| Локальная БД | SQLite (stdlib) | DuckDB (аналитика) | — |

## Тестирование

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Unit | **pytest** | unittest | pytest — стандарт |
| Параметризация | `@pytest.mark.parametrize` | — | табличные тесты |
| Моки | `unittest.mock` / `monkeypatch` | — | — |
| E2E (веб) | Playwright | — | — |

## Качество

| Задача | Рекомендация | Альтернатива |
|---|---|---|
| Линтер+форматтер | **ruff** | black + isort + flake8 |
| Типы | **mypy** (strict) / pyright | — |
| Пакетный менеджер | **uv** | pip + venv |

## Related

- [rules.md](rules.md)
- [shared/api-design.md](../shared/api-design.md)
