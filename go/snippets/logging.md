---
id: go-logging
title: "Structured logging: log/slog"
lang: go
min_version: "1.21"
category: snippet
tags: [slog, logging, observability, stdlib]
status: stable
updated: 2026-09-06
---

# Structured logging (slog)

**Когда использовать** — логирование в Go 1.21+: stdlib `log/slog`.
**Когда НЕ использовать** — нужна максимальная производительность: `zap` (см. [decisions.md](../decisions.md)).

## Код

```go
package main

import (
	"context"
	"log/slog"
	"os"
)

func NewLogger(level slog.Level) *slog.Logger {
	handler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: level,
	})
	return slog.New(handler)
}

func main() {
	logger := NewLogger(slog.LevelInfo)
	slog.SetDefault(logger) // для пакетов, использующих slog.Info и т.п.

	// Структурные поля: key-value, не fmt.Sprintf.
	logger.Info("request",
		"method", "GET",
		"path", "/api/v1/items",
		"duration_ms", 42,
	)
	logger.Error("failed", "err", os.ErrInvalid, "retry", 3)

	// Кастомный уровень.
	if logger.Enabled(context.Background(), slog.LevelDebug) {
		logger.Debug("detail", "value", 42)
	}

	// Передача через context (для глубоких уровней без параметров).
	ctx := context.WithValue(context.Background(), loggerKey{}, logger)
	l := LoggerFrom(ctx)
	l.Info("processing", "id", "abc")
}

type loggerKey struct{}

func WithLogger(ctx context.Context, l *slog.Logger) context.Context {
	return context.WithValue(ctx, loggerKey{}, l)
}

func LoggerFrom(ctx context.Context) *slog.Logger {
	if l, ok := ctx.Value(loggerKey{}).(*slog.Logger); ok {
		return l
	}
	return slog.Default()
}
```

## Pitfalls

- Не `fmt.Sprintf` в сообщении: `logger.Info("request to " + url)` → `logger.Info("request", "url", url)`.
- Не логируйте чувствительные данные (токены, PII) — фильтруйте на уровне handler'а.
- `LevelDebug` — отключайте в production (настройкой уровня, не удалением вызовов).
- `slog.SetDefault` — глобальное состояние; предпочитайте явную передачу логгера.
- `err` в поле — slog сам вызовёт `Error()`.

## Related

- [http-server.md](http-server.md)
- [decisions.md — Логирование](../decisions.md)
