---
id: go-http-client
title: "HTTP client: context, таймауты, JSON, ретраи"
lang: go
min_version: "1.27"
category: snippet
tags: [http, client, context, timeout, retry, json]
status: stable
updated: 2026-09-07
---

# HTTP client (stdlib)

**Когда использовать** — вызовы внешнего HTTP API из Go-сервиса: JSON-запросы, таймауты, ретраи.
**Когда НЕ использовать** — gRPC-сервисы: `google.golang.org/grpc` (см. [decisions.md](../decisions.md)).

## Код

```go
package client

import (
	"bytes"
	"context"
	"encoding/json/v2"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"
)

// Один общий клиент на приложение: пул соединений переиспользуется.
var client = &http.Client{
	Timeout: 15 * time.Second, // жёсткий потолок на весь запрос (включая ретраи)
	Transport: &http.Transport{
		MaxIdleConns:        100,
		MaxIdleConnsPerHost: 16,
		IdleConnTimeout:     90 * time.Second,
	},
}

// APIError — непрозрачный статус от удалённого сервиса.
type APIError struct {
	Status int
	Body   string
	Err    error
}

func (e *APIError) Error() string {
	if e.Err != nil {
		return e.Err.Error()
	}
	return fmt.Sprintf("unexpected status %d: %s", e.Status, e.Body)
}

// GetJSON — GET + decode в T.
func GetJSON[T any](ctx context.Context, rawURL string) (T, error) {
	var out T
	err := doJSON(ctx, http.MethodGet, rawURL, nil, &out)
	return out, err
}

// PostJSON — POST body (marshal в JSON) + decode в out (может быть nil).
func PostJSON[T any](ctx context.Context, rawURL string, body any, out *T) error {
	return doJSON(ctx, http.MethodPost, rawURL, body, out)
}

func doJSON[T any](ctx context.Context, method, rawURL string, body any, out *T) error {
	var payload []byte
	if body != nil {
		var err error
		payload, err = json.Marshal(body)
		if err != nil {
			return fmt.Errorf("marshal body: %w", err)
		}
	}

	var err error
	delay := 200 * time.Millisecond
	for attempt := 0; ; attempt++ {
		err = doOnce(ctx, method, rawURL, payload, out)
		if err == nil || !isRetryable(err) || attempt >= 2 {
			break
		}
		// Exponential backoff: 200ms, 800ms (с учётом отмены).
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(delay):
		}
		delay *= 4
	}
	return err
}

func doOnce[T any](ctx context.Context, method, rawURL string, payload []byte, out *T) error {
	req, err := http.NewRequestWithContext(ctx, method, rawURL, bytes.NewReader(payload))
	if err != nil {
		return fmt.Errorf("new request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	if payload != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	resp, err := client.Do(req)
	if err != nil {
		return &APIError{Err: fmt.Errorf("do request: %w", err)}
	}
	defer resp.Body.Close()

	// 4xx (кроме 408/429) — не ретраим: ошибка запроса, повтор не поможет.
	if resp.StatusCode >= 400 {
		b, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<10))
		return &APIError{Status: resp.StatusCode, Body: string(bytes.TrimSpace(b))}
	}

	// Ограничиваем размер ответа: защита от «слитого» тела.
	if out == nil {
		_, _ = io.Copy(io.Discard, resp.Body)
		return nil
	}
	// v2: стриминг-декодирование из io.Reader.
	if err := json.UnmarshalRead(io.LimitReader(resp.Body, 1<<20), out); err != nil {
		return fmt.Errorf("decode response: %w", err)
	}
	return nil
}

func isRetryable(err error) bool {
	var apiErr *APIError
	if !errors.As(err, &apiErr) {
		return false // сетевая ошибка/таймаут — ретраим
	}
	switch apiErr.Status {
	case http.StatusRequestTimeout, http.StatusTooManyRequests,
		http.StatusBadGateway, http.StatusServiceUnavailable, http.StatusGatewayTimeout:
		return true
	default:
		return false
	}
}

// Пример использования:
//
//	type Item struct {
//		ID   string `json:"id"`
//		Name string `json:"name"`
//	}
//
//	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
//	defer cancel()
//	item, err := GetJSON[Item](ctx, "https://api.example.com/items/1")
```

## Pitfalls

- **Не создавайте `http.Client` на запрос** — теряется пул соединений (TCP+TLS handshake на каждый вызов).
- `client.Timeout` — потолок на **весь** запрос, включая чтение тела; для лонгридинга используйте только `context`.
- `io.LimitReader` на теле ответа обязателен: без него злонамеренный/сломанный API может слить гигабайты в память.
- `resp.Body.Close()` — всегда (иначе соединение не вернётся в пул).
- Ретраите только идемпотентные запросы (GET) или явно идемпотентные POST (идемпотентный ключ в теле/заголовке).
- `url.Parse`-ошибки проверяйте до `client.Do`, если URL собирается динамически.

## Related

- [http-server.md](http-server.md)
- [context.md](context.md)
- [json.md](json.md)
- [decisions.md](../decisions.md)
