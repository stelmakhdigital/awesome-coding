---
id: go-decisions
title: Go Decisions
lang: go
min_version: "1.21"
category: decisions
tags: [decisions, libraries, choices, ecosystem]
status: stable
updated: 2026-09-06
---

# Go — Decision Tables

Что выбрать и когда. Рекомендация — конкретный подход + минимальная версия.

## HTTP

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Роутинг | stdlib `http.ServeMux` (1.22+) | `go-chi/chi` v5 | сложные мидлвари, группировка, wildcard'и |
| Полный фреймворк | chi + slog | `labstack/echo`, `gin-gonic/gin` | нужен готовый стек (валидация, биндинг) |
| gRPC | `google.golang.org/grpc` | — | стандарт для service-to-service |
| HTTP/2, h2c | stdlib (включено) | — | — |

## Конфигурация и CLI

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| CLI-флаги | stdlib `flag` | `spf13/cobra` | подкоманды, help, автодополнение |
| Конфиг-файлы | stdlib + `encoding/json`/YAML | `spf13/viper` | нужен env-override, watch, много форматов |

## Данные

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| SQL | `database/sql` + драйвер (`pgx`, `go-sql-driver/mysql`) | `sqlc` (типобезопасные запросы) | сложные запросы, миграции |
| ORM | без ORM (sqlc / чистый SQL) | `entgo.io/ent` | сложная доменная модель, graph-запросы |
| Migrations | `golang-migrate/migrate` | `golang-migrate` в CI | — |
| Redis | `redis/go-redis` v9 | — | — |

## JSON

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Marshal/Unmarshal | stdlib `encoding/json` | `goccy/go-json` | критичная производительность (проверьте бенчмарком) |
| Строгий парсинг | `dec.DisallowUnknownFields()` | — | API-контракты |

## Логирование

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Структурный лог | stdlib `log/slog` (1.21+) | `go.uber.org/zap` | нужна максимальная производительность |

## Тесты

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Unit-тесты | stdlib `testing` | — | всегда |
| Assert'ы | stdlib (`t.Errorf`) | `stretchr/testify` (assert/require) | громоздкие проверки, mock'и |
| Mock'и | ручные (интерфейсы) | `go.uber.org/mock` (mockgen) | много mock'ов |
| HTTP-тесты | `httptest` | — | — |

## Конкурентность

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Ограничение параллелизма | `errgroup.SetLimit` (1.20+) | ручной semaphore-канал | — |
| Синхронизация тестов | `testing/synctest` (1.24+, эксперимент.) | — | детерминированные конкурентные тесты |

## Утилиты

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Срезы/мапы | stdlib `slices`/`maps` (1.21+) | — | всегда |
| UUID | `google/uuid` | `github.com/gofrs/uuid` | — |
| Валидация | stdlib + собственные проверки | `go-playground/validator` | DTO с кучей тегов |
