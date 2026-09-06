---
id: kotlin-decisions
title: "Kotlin Decisions (Compose, DI, HTTP, БД)"
lang: kotlin
min_version: "2.3"
category: decisions
tags: [decisions, compose, hilt, ktor, retrofit, room, choices]
status: stable
updated: 2026-09-06
---

# Kotlin — таблицы решений

## UI (Android)

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Новый Android-UI | **Jetpack Compose** | Views/XML | — |
| Миграция с Views | Compose (постепенно, `ViewCompositionLocal`) | — | новые фичи — Compose |
| Сложные анимации | Compose Animations / ReCompose | Lottie | — |

## Архитектура и DI

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| DI (Android) | **Hilt** | Koin | Hilt — стандарт, Koin — лёгче |
| DI (JVM-сервер) | Koin / кастомный | Spring (Java-экосистема) | — |
| Архитектура | MVVM (ViewModel + Compose) | MVI (сложные состояния) | — |
| Слой данных | Repository + UseCase (опц.) | прямой доступ | DDD-уровень ≥ 1 |

## Сеть

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| HTTP-клиент (Android) | **Ktor Client** | Retrofit | Ktor — мультиплатформенный, корутины из коробки |
| HTTP-клиент (JVM) | Ktor Client | OkHttp + Retrofit | — |
| WebSocket | Ktor (WebSocket) | OkHttp | — |
| Миграция/ретраи | Ktor `HttpTimeout` + retry-оператор | — | — |

## Данные

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Локальная БД (Android) | **Room** (SQLDelight) | SQLite напрямую | Room — типобезопасно |
| Кэш (Android) | DataStore (ключ-значение) | `SharedPreferences` | DataStore — корутины, типизация |
| Сериализация | **kotlinx.serialization** | Gson/Moshi | kotlinx — stdlib-уровень, multiplatform |

## Асинхронность

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Асинхронность | **Корутины** (`suspend`) | callbacks | — |
| Потоки событий | `Flow` / `StateFlow` | `Channel` (hot) | UI-состояние — StateFlow |
| Параллелизм | `async` + `awaitAll` | — | независимые задачи |

## Related

- [rules.md](rules.md)
- [snippets/](snippets/README.md)
