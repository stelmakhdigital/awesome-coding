---
id: shared-configuration
title: "Shared: Configuration (кросс-языковые принципы)"
lang: shared
min_version: null
category: concept
tags: [configuration, env, 12-factor, secrets, validation]
status: stable
updated: 2026-09-06
---

# Configuration — принципы

**Когда использовать** — конфигурация приложения (сервисы, CLI, бэкенды).
**Когда НЕ использовать** — конфигурация UI/фич для конечного пользователя (другая задача).

## Принципы (12-factor)

1. **Конфиг — в окружении**, не в коде: env-переменные / secret manager / config-файл (по приоритету).
2. **Приоритет**: флаги CLI > env > config-файл > дефолты.
3. **Секреты — отдельно** (secret manager / env), не в config-файле, не в репо.
4. **Валидация на старте**: приложение не стартует с невалидным конфигом (fail fast).
5. **Один источник истины**: не дублируйте значения в коде и конфиге.
6. **Имена — предсказуемые**: `SCREAMING_SNAKE_CASE` для env (`DATABASE_URL`, `LOG_LEVEL`).

## ✅ / ❌

- ✅ `DATABASE_URL` из env, валидация на старте
- ❌ `const dbUrl = "postgres://..."` в коде
- ✅ Дефолты для небезопасных значений (таймауты, логи)
- ❌ Обязательные значения без дефолта «потом посмотрим»
- ✅ Секрет из secret manager (Vault/AWS SM/GCP SM)
- ❌ Секрет в config-файле в репо / в логах
- ✅ Типизированный конфиг (структура + валидация), не `map[string]string`
- ❌ «Магические» env-имена без документации
- ✅ Документация: список всех переменных + дефолты + примеры

## Пример (Go)

```go
// Типизированный конфиг: валидация на старте, дефолты явные.
type Config struct {
    DatabaseURL string        `env:"DATABASE_URL" envRequired:"true"`
    LogLevel    string        `env:"LOG_LEVEL" envDefault:"info"`
    HTTPTimeout time.Duration `env:"HTTP_TIMEOUT" envDefault:"30s"`
}

func Load() (Config, error) {
    var c Config
    if err := env.Parse(&c); err != nil { // github.com/caarlos0/env/v11
        return Config{}, fmt.Errorf("load config: %w", err)
    }
    if c.LogLevel != "debug" && c.LogLevel != "info" && c.LogLevel != "warn" && c.LogLevel != "error" {
        return Config{}, fmt.Errorf("invalid LOG_LEVEL: %q", c.LogLevel)
    }
    return c, nil
}
```

## По языкам

| Язык | Инструменты |
|---|---|
| Go | `caarlos0/env` (v11), `kelseyhightower/envconfig` |
| C# | `IConfiguration` (M.E.Configuration), `IOptions<T>` |
| Python | `pydantic-settings`, `python-decouple` |
| TS/JS | `zod` + `process.env`, `envalid` |
| Kotlin | `kotlinx.serialization` + env |
| C | `getenv` + ручная валидация |
| Bash | `: "${VAR:?required}"`, `set -u` |

## Related

- [security.md](security.md) — секреты
- [observability.md](observability.md) — `LOG_LEVEL` в production
