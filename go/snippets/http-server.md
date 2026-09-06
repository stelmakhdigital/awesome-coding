---
id: go-http-server
title: HTTP server (stdlib, Go 1.22+)
lang: go
min_version: "1.22"
category: snippet
tags: [http, net, server, stdlib]
status: stable
updated: 2026-09-06
---

# HTTP server (stdlib)

**Когда использовать** — production HTTP-сервис без сложного роутинга/мидлварей.
**Когда НЕ использовать** — сложные цепочки мидлварей, группировка, wildcard'и: `chi` (см. [decisions.md](../decisions.md)).

## Код

```go
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func handleCreateItem(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	_, _ = w.Write([]byte(`{"id":"1"}`))
}

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}))

	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	})
	mux.HandleFunc("POST /api/v1/items", handleCreateItem)
	// Go 1.22+: метод + паттерн; {id} — path-параметр.
	mux.HandleFunc("GET /api/v1/items/{id}", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		_ = id
	})

	srv := &http.Server{
		Addr:              ":8080",
		Handler:           mux,
		ReadTimeout:       5 * time.Second,
		ReadHeaderTimeout: 5 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	errCh := make(chan error, 1)
	go func() { errCh <- srv.ListenAndServe() }()

	select {
	case <-ctx.Done():
		logger.Info("shutting down")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := srv.Shutdown(shutdownCtx); err != nil {
			logger.Error("graceful shutdown failed", "err", err)
		}
	case err := <-errCh:
		if !errors.Is(err, http.ErrServerClosed) {
			logger.Error("server error", "err", err)
			os.Exit(1)
		}
	}
}
```

## Pitfalls

- Без таймаутов — уязвимость к slowloris.
- `http.ErrServerClosed` — нормальный результат после `Shutdown`, не ошибка.
- Handler'ы не должны блокировать: тяжёлая работа — в goroutine с ctx или в воркерах.
- `w.Write` возвращает `error` — не игнорируйте его в ответе с данными.

## Related

- [graceful-shutdown.md](graceful-shutdown.md)
- [patterns/http-middleware.md](../patterns/http-middleware.md)
- [logging.md](logging.md)
