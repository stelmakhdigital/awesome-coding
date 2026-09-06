---
id: go-context
title: Context: timeout, cancellation, values
lang: go
min_version: "1.21"
category: snippet
tags: [context, cancellation, timeout, stdlib]
status: stable
updated: 2026-09-06
---

# Context

**Когда использовать** — передача deadline/cancellation/запрососпецифичных данных через границы функций.
**Когда НЕ использовать** — как параметр функции «для красоты»: ctx — только когда есть отмена/таймаут/значения.

## Код

```go
package service

import (
	"context"
	"errors"
	"time"
)

// --- Минимальные доменные типы (заглушки для самодостаточности) ---

type Result struct {
	Value string
}

type client struct{}

func (client) Call(ctx context.Context, id string) (Result, error) {
	if err := ctx.Err(); err != nil {
		return Result{}, err
	}
	return Result{Value: id}, nil
}

type Service struct {
	client client
}

// ctx — первый аргумент, имя ctx.
func (s *Service) DoWork(ctx context.Context, id string) (Result, error) {
	// 1. Таймаут для внешней операции.
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel() // ОБЯЗАТЕЛЬНО: иначе утечка timer'а

	// 2. Проверка отмены до дорогой операции.
	if err := ctx.Err(); err != nil {
		return Result{}, err // context.Canceled или context.DeadlineExceeded
	}

	// 3. Отмена извне: реакция на ctx.Done().
	done := make(chan struct{})
	go func() {
		select {
		case <-ctx.Done():
			// локальная cleanup
		case <-done:
		}
	}()
	defer close(done)

	res, err := s.client.Call(ctx, id) // клиент обязан уважать ctx
	if err != nil {
		if errors.Is(err, context.DeadlineExceeded) {
			return Result{}, errors.New("upstream timeout")
		}
		return Result{}, err
	}
	return res, nil
}

//  4. Values — только запрососпецифичные данные (user ID, trace ID),
//     не параметры, которые можно передать явно.
type userKey struct{}

func WithUser(ctx context.Context, uid string) context.Context {
	return context.WithValue(ctx, userKey{}, uid)
}

func UserFrom(ctx context.Context) (string, bool) {
	uid, ok := ctx.Value(userKey{}).(string)
	return uid, ok
}
```

## Pitfalls

- Не храните `ctx` в структурах — передавайте аргументом.
- Не передавайте `nil` — только `context.Background()`/`TODO()` (TODO — только в тестах/заглушках).
- `cancel()`/`WithTimeout` без `defer cancel()` — утечка.
- Ключи `WithValue` — unexported типы, иначе коллизии между пакетами.
- Не используйте ctx для опциональных параметров — это антипаттерн.

## Related

- [goroutines.md](goroutines.md)
- [graceful-shutdown.md](graceful-shutdown.md)
