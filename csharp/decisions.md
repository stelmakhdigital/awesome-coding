---
id: csharp-decisions
title: C# Decisions
lang: csharp
min_version: "10"
category: decisions
tags: [decisions, libraries, choices, ecosystem]
status: stable
updated: 2026-09-06
---

# C# — таблицы решений

## Сериализация

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| JSON | `System.Text.Json` + **source generation** | `Newtonsoft.Json` | Newtonsoft — только legacy-код |
| Скорость JSON | `JsonSerializerOptions` с source gen | `AperJSON` (проверьте бенчмарком) | горячий путь |
| XML | `System.Xml.Linq` | — | legacy-форматы |

## Логирование и DI

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Логирование | `Microsoft.Extensions.Logging` (`ILogger<T>`) | `Serilog` (синки: файл, ELK) | нужен конкретный sink |
| DI | `Microsoft.Extensions.DependencyInjection` | `Autofac` | сложное декорирование/наследование |
| Конфигурация | Options pattern (`IOptions<T>`, `IOptionsSnapshot<T>`) | прямое чтение `IConfiguration` | несколько секций конфига |

## Данные

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| ORM | `EF Core` | `Dapper` (чистый SQL) | простые CRUD-запросы, максимум скорости |
| Миграции | EF Core Migrations | `DbUp` | — |
| Кэш | `MemoryCache` / `DistributedCache` (Redis) | — | — |

## HTTP

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| HTTP-клиент | `IHttpClientFactory` + `Microsoft.Extensions.Http.Resilience` | `HttpClient` напрямую | — |
| Ретраи/таймауты | resilience pipeline (встроенный) | `Polly` напрямую | legacy |
| API-сервер | ASP.NET Core Minimal APIs | Controllers | сложная маршрутизация, версии API |

## Тесты

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Unit-тесты | `xUnit` | `MSTest`, `NUnit` | — |
| Assert'ы | `xunit.assert` (встроен) | `FluentAssertions` | читаемые цепочки |
| Mock'и | `NSubstitute` | `Moq` | — |
| Integration | `WebApplicationFactory<T>` (ASP.NET Core) | Testcontainers (БД) | нужна реальная БД |

## Разное

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Валидация | `FluentValidation` | DataAnnotations | сложные правила, переиспользование |
| Планировщик | `PeriodicTimer` / `System.Threading.Timer` | `Hangfire`, `Quartz` | распределённые задачи, персистентная очередь |
| Маппинг DTO | ручной (явный) | `Mapster`, `AutoMapper` | много DTO, одинаковые поля |
| Время | `TimeProvider` | `DateTime.Now` | всегда (тестируемость) |

## Related

- [rules.md](rules.md)
- [snippets/](snippets/README.md)
