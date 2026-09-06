---
id: shared-observability
title: "Shared: Observability (логи, метрики, трейсинг)"
lang: shared
min_version: null
category: concept
tags: [observability, logging, metrics, tracing, opentelemetry]
status: stable
updated: 2026-09-06
---

# Observability — принципы

**Когда использовать** — любой production-код (сервисы, бэкенды, инфраструктура).
**Когда НЕ использовать** — локальные скрипты/одноразовые утилиты.

## Три столпа

| Столп | Вопрос | Формат |
|---|---|---|
| **Логи** | «Что случилось?» | структурированные события (JSON) |
| **Метрики** | «Как система ведёт себя во времени?» | counter/gauge/histogram |
| **Трейсы** | «Через что прошёл запрос?» | spans + trace_id |

## Логи

1. **Структурированные** (ключ-значение), не строки: `{ts, level, msg, order_id, ...}`.
2. **Уровни**: `DEBUG` (диагностика), `INFO` (жизненный цикл), `WARN` (аномалия с обработкой), `ERROR` (сбой).
3. **Correlation ID** (request/trace id) — в каждом событии запроса.
4. **Не логировать**: секреты, PII, тело запроса целиком (только идентификаторы).
5. **Одна строка = одно событие** (не «рассказ» из 10 строк).

## Метрики

1. **RED** для сервисов: **R**ate (запросы/с), **E**rrors (доля), **D**uration (латентность, percentiles p50/p95/p99).
2. **USE** для ресурсов: **U**tilization, **S**aturation, **E**rrors (CPU, память, пулы, очереди).
3. **Histogram — не average**: среднее скрывает хвосты; нужны percentiles.
4. **Метки (labels) — низкая кардинальность**: `method, status, route` — да; `user_id` — нет.
5. Базовый набор: запросы, ошибки, латентность, очередь, память, GC.

## Трейсинг

1. **OpenTelemetry** — стандарт: SDK собирает spans, экспорт в backend (Jaeger/Tempo/OTLP).
2. **Span на каждую границу**: HTTP-запрос, вызов сервиса, запрос к БД, очередь.
3. **Context propagation**: trace_id пробрасывается в заголовках (`traceparent`) и в сообщениях очередей.
4. **Сэмплирование**: в production — 1–10% (или head-based по ошибкам), не 100%.

## ✅ / ❌

- ✅ `log.Info("order created", "order_id", id, "total", total)`
- ❌ `log.Info("created order " + id + " total " + total)` (конкатенация)
- ✅ Метрика `http_requests_total{method, route, status}`
- ❌ Метрика с `user_id` в label (высокая кардинальность)
- ✅ Trace через все сервисы запроса
- ❌ «Логи вместо трейсов» для распределённой отладки

## По языкам

| Язык | Логи | Трейсинг |
|---|---|---|
| Go | `log/slog` | OTel Go SDK |
| C# | `Microsoft.Extensions.Logging` | OTel .NET |
| Python | `structlog`/`logging` | OTel Python |
| TS/JS | `pino`/`winston` | OTel JS |
| Kotlin | `SLF4J`/`kotlin-logging` | OTel Java |

## Related

- [go/snippets/logging.md](../go/snippets/logging.md) — slog
- [csharp/snippets/logging.md](../csharp/snippets/logging.md) — M.E.Logging
- [error-handling.md](error-handling.md) — ошибки в логах
