---
id: go-graceful-shutdown
title: Graceful shutdown: signal.NotifyContext
lang: go
min_version: "1.21"
category: snippet
tags: [signals, lifecycle, shutdown, stdlib]
status: stable
updated: 2026-09-06
---

# Graceful shutdown

**Когда использовать** — любой long-running сервис: корректное завершение по SIGINT/SIGTERM.
**Когда НЕ использовать** — кратковременные скрипты: достаточно `os.Exit`.

## Код

```go
package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"
)

func main() {
	logger := slog.Default()

	// ctx отменяется по SIGINT/SIGTERM.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	var wg sync.WaitGroup

	// Фоновые компоненты получают ctx и завершаются по его отмене.
	wg.Add(1)
	go func() {
		defer wg.Done()
		runWorker(ctx, logger)
	}()

	// Ожидание сигнала.
	<-ctx.Done()
	logger.Info("shutdown signal received")

	// Дедлайн на завершение: если компоненты не успели — форсируем.
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	wg.Wait() // компоненты завершаются по ctx (уже отменён)
	logger.Info("shutdown complete")

	_ = shutdownCtx // если нужен отдельный дедлайн — используйте его в Shutdown-методах
}

func runWorker(ctx context.Context, logger *slog.Logger) {
	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			logger.Info("worker stopping")
			return
		case <-ticker.C:
			// работа
		}
	}
}
```

## Pitfalls

- `defer stop()` — обязательно, иначе утечка signal handler'а.
- Компоненты должны проверять `ctx.Done()`/`ctx.Err()`, а не «узнавать» о завершении иначе.
- `http.Server.Shutdown` — отдельный дедлайн (см. [http-server.md](http-server.md)).
- Не блокируйте main-горутину в ожидании компонентов без дедлайна.

## Related

- [http-server.md](http-server.md)
- [context.md](context.md)
