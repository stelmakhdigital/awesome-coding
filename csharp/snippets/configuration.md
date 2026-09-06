---
id: csharp-configuration
title: "Configuration: Options pattern (IOptions, валидация, hot-reload)"
lang: csharp
min_version: "10"
category: snippet
tags: [configuration, options, ioptions, validation, env, 12-factor]
status: stable
updated: 2026-09-07
---

# Configuration: Options pattern

**Когда использовать** — любой внешний конфиг .NET-сервиса: секции `appsettings.json`, env-переменные, секреты.
**Когда НЕ использовать** — одна-две константы: прямой `IConfiguration`-read допустим; распределённый конфиг: Consul/Vault-провайдеры поверх того же `IConfiguration`.

## Код

```csharp
using Microsoft.Extensions.Options;

// 1) ПOCO-настройки: одна секция — один класс.
sealed class StorageOptions
{
    public const string SectionName = "Storage";
    public string? Bucket { get; init; }
    public int TimeoutSeconds { get; init; } = 30;
}

// 2) Валидация: fail fast на старте, а не на первом использовании.
sealed class StorageOptionsValidator : IValidateOptions<StorageOptions>
{
    public OptionsValidationResult Validate(string name, StorageOptions options)
    {
        if (string.IsNullOrWhiteSpace(options.Bucket))
        {
            return OptionsValidationResult.Fail("Storage:Bucket обязателен");
        }
        if (options.TimeoutSeconds is < 1 or > 300)
        {
            return OptionsValidationResult.Fail("Storage:TimeoutSeconds: 1..300");
        }
        return OptionsValidationResult.Success;
    }
}

// 3) Регистрация (Program.cs): секция конфигурации + валидация на старте.
builder.Services.Configure<StorageOptions>(
    builder.Configuration.GetSection(StorageOptions.SectionName));
builder.Services.AddOptions<StorageOptions>()
    .ValidateOnStart()          // бросает OptionsValidationException при старте
    .Validate<StorageOptionsValidator>();

// 4) Потребление: primary constructor (C# 12+).
sealed class FileStorage(IOptions<StorageOptions> options)
{
    private readonly StorageOptions _opts = options.Value;

    public TimeSpan Timeout => TimeSpan.FromSeconds(_opts.TimeoutSeconds);
}

// 5) Hot-reload (scoped): IOptionsSnapshot перечитывает секцию при каждом
//    scoped-создании — работает с ConfigurationReloadOnChange-источниками.
// sealed class PerRequestStorage(IOptionsSnapshot<StorageOptions> options) { ... }
```

`appsettings.json`:

```json
{
  "Storage": {
    "Bucket": "items-prod",
    "TimeoutSeconds": 30
  }
}
```

Env-override (12-factor): `Storage__Bucket=items-staging` (двойное подчёркивание = разделитель секций).

## Pitfalls

- **`IOptions` vs `IOptionsSnapshot` vs `IOptionsMonitor`**: `IOptions` — singleton, значение фиксируется на старте; `IOptionsSnapshot` — scoped, перечитывается на каждый request; `IOptionsMonitor` — live-обновление + события. Не тот выбор = «конфиг не обновляется» или «singleton держит устаревшее значение».
- **Секреты не в `appsettings.json`**: env, User Secrets (dev), Vault — в проде.
- `ValidateOnStart` обязателен: без него опечатка в ключе падает в рантайме на первом запросе.
- Не читайте `IConfiguration` напрямую в десятках классов — только через Options (валидация + DI + тесты).
- Числа/даты из env — парсите в POCO (сделает `Configure<T>`), не `int.Parse` по всему коду.

## Related

- [http-server.md](http-server.md)
- [logging.md](logging.md)
- [shared/configuration.md](../../shared/configuration.md)
