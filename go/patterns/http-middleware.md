---
id: go-http-middleware
title: HTTP Middleware
lang: go
min_version: "1.22"
category: pattern
tags: [http, middleware, server, stdlib]
status: stable
updated: 2026-09-06
---

# HTTP Middleware

**Проблема** — поперечные функции (логирование, auth, recovery) дублируются в каждом handler'е.
**Решение** — мидлварь как `func(http.Handler) http.Handler` + цепочка.
**Когда использовать** — 2+ handler'ов с общей поперечной логикой.
**Когда НЕ использовать** — одна поперечная функция для одного handler'а: вызовите её внутри.

## Код

```go
package middleware

import (
	"log/slog"
	"net/http"
	"time"
)

type Middleware func(http.Handler) http.Handler

// Логирование запросов.
func Logging(logger *slog.Logger) Middleware {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			next.ServeHTTP(w, r)
			logger.Info("request",
				"method", r.Method,
				"path", r.URL.Path,
				"duration_ms", time.Since(start).Milliseconds(),
			)
		})
	}
}

// Recovery: паника -> 500, без падения процесса.
func Recovery(logger *slog.Logger) Middleware {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			defer func() {
				if p := recover(); p != nil {
					logger.Error("panic recovered", "panic", p)
					http.Error(w, "internal error", http.StatusInternalServerError)
				}
			}()
			next.ServeHTTP(w, r)
		})
	}
}

// Цепочка: первый в списке — самый внешний.
func Chain(h http.Handler, mws ...Middleware) http.Handler {
	for i := len(mws) - 1; i >= 0; i-- {
		h = mws[i](h)
	}
	return h
}

// Применение.
// mux := http.NewServeMux()
// handler := Chain(mux,
//     Recovery(logger), // внешний: ловит паники из всех
//     Logging(logger),
// )
```

## Pitfalls

- **Порядок важен**: `Chain(mux, A, B)` — A снаружи, B внутри. Логирование обычно снаружи auth (видеть и отклонённые).
- Мидлварь не должен «проглатывать» ошибки handler'а без логирования.
- Для записи status code — оберните `ResponseWriter` (кастомный тип с полем status).
- Не делайте тяжёлую работу в мидлваре до `next.ServeHTTP` — это задерживает все запросы.

## Related

- [snippets/http-server.md](../snippets/http-server.md)
- [snippets/logging.md](../snippets/logging.md)
