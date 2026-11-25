---
id: shared-configuration
title: "Shared: Configuration (кросс-языковые принципы)"
lang: shared
min_version: null
category: concept
tags: [configuration, env, 12-factor, secrets, validation]
status: stable
updated: 2026-11-25
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
package config

import (
	"fmt"
	"os"
	"time"
)

// Типизированный конфиг: дефолты явные, обязательное проверяем на старте.
type Config struct {
	DatabaseURL string
	LogLevel    string
	HTTPTimeout time.Duration
}

// Load читает окружение и не оставляет невалидного значения без ошибки.
func Load() (Config, error) {
	c := Config{
		DatabaseURL: os.Getenv("DATABASE_URL"),
		LogLevel:    orDefault(os.Getenv("LOG_LEVEL"), "info"),
	}
	var err error
	if c.HTTPTimeout, err = durationOr("HTTP_TIMEOUT", 30*time.Second); err != nil {
		return Config{}, err
	}

	switch c.LogLevel {
	case "debug", "info", "warn", "error":
	default:
		return Config{}, fmt.Errorf("invalid LOG_LEVEL: %q", c.LogLevel)
	}
	if c.DatabaseURL == "" {
		return Config{}, fmt.Errorf("DATABASE_URL is required")
	}
	return c, nil
}

func orDefault(v, def string) string {
	if v == "" {
		return def
	}
	return v
}

func durationOr(key string, def time.Duration) (time.Duration, error) {
	raw := os.Getenv(key)
	if raw == "" {
		return def, nil
	}
	d, err := time.ParseDuration(raw)
	if err != nil {
		return 0, fmt.Errorf("parse %s: %w", key, err)
	}
	return d, nil
}

// Проверка при сборке: блок — рабочий код, а не выдержка.
var (
	_ = Load
	_ = orDefault
	_ = durationOr
)
```

## По языкам

| Язык | Инструменты |
|---|---|
| Go | stdlib `os.Getenv` (ниже) или `caarlos0/env` (v11), `kelseyhightower/envconfig` |
| C# | `IConfiguration` (M.E.Configuration), `IOptions<T>` |
| Python | `pydantic-settings`, `python-decouple` |
| TS/JS | `zod` + `process.env`, `envalid` |
| Kotlin | `kotlinx.serialization` + env |
| C | `getenv` + ручная валидация |
| Bash | `: "${VAR:?required}"`, `set -u` |

## Related

- [security.md](security.md) — секреты
- [observability.md](observability.md) — `LOG_LEVEL` в production
