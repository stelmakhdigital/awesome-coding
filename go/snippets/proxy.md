---
id: go-proxy
title: "Go: прокси и границы времени — таймауты, отмена, 502/503/504"
lang: go
min_version: "1.22"
category: snippet
tags: [proxy, reverse-proxy, timeout, cancellation, streaming, maxbytes, http, statuses]
status: stable
updated: 2026-11-25
---

# Прокси и границы времени: таймауты, отмена, 502/503/504

**Когда использовать** — сервис стоит прослойкой перед другим сервисом и должен честно отвечать клиенту: песочница исполнения, внутренний API, прокси к медленному внешнему источнику, стриминг через себя.
**Когда НЕ использовать** — «просто прокинуть хост» без логики: это работа реверс-прокси на краю ([../cicd/docker.md](../../cicd/docker.md) + Caddy/nginx). Прокси в приложении — это место, где появляется задержка, потерянные заголовки и свои коды ошибок; пусть оно будет одним, а не пятью.

## ReverseProxy с понятными кодами ошибок

```go
// Package proxy — проброс запроса во внутренний сервис с границами времени и
// различимыми ответами об отказе.
package proxy

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"net/http/httputil"
	"net/url"
	"time"
)

// New проксирует на target. headerTimeout — сколько ждём заголовок ответа;
// полной «длительности ответа» в HTTP-клиенте нет по определению: тело может
// читаться минуты.
func New(target *url.URL, headerTimeout time.Duration, log *slog.Logger) *httputil.ReverseProxy {
	proxy := &httputil.ReverseProxy{
		Rewrite: func(pr *httputil.ProxyRequest) {
			pr.SetURL(target)
			// Без SetXForwarded внутренний сервис видит localhost как клиента
			// и не может ни логировать клиента, ни ограничивать его по адресу.
			pr.SetXForwarded()
			// Origin перезаписывается адресом апстрима: у того своя проверка Origin,
			// и чужой источник он отклонил бы.
			pr.Out.Header.Set("Origin", target.Scheme+"://"+target.Host)
		},
		Transport: &http.Transport{
			// Ответ без заголовка за этот срок — ошибка, а не «ждём вечно».
			ResponseHeaderTimeout: headerTimeout,
			// Конечный хост: столько соединений на него держим, сверх — очередь.
			MaxIdleConnsPerHost: 32,
			// Сжатие не пережимаем дважды: апстрим уже умеет.
			DisableCompression: false,
			ForceAttemptHTTP2:  true,
			// Сокеты, висящие после отмены запроса, — самая частая «утечка
			// соединений» в прокси-обёртках.
			IdleConnTimeout: 60 * time.Second,
		},
		// Поток (SSE, ndjson, скачивание) должен уходить клиенту частями, а не
		// копиться в буфере прокси.
		FlushInterval: -time.Millisecond,
		ErrorHandler: func(w http.ResponseWriter, r *http.Request, err error) {
			log.Error("proxy upstream",
				"host", target.Host, "path", r.URL.Path, "err", err)

			switch {
			case errors.Is(err, context.Canceled):
				// Клиент ушёл сам: писать уже некому, статус не нужен.
			case errors.Is(err, context.DeadlineExceeded):
				http.Error(w, "upstream timeout", http.StatusGatewayTimeout)
			default:
				// Апстрим не поднялся / отказал соединением: это «сервис
				// недоступен», а не «внутренняя ошибка прокси».
				http.Error(w, "upstream unavailable", http.StatusServiceUnavailable)
			}
		},
	}
	return proxy
}

// WithDeadline ограничивает весь проксированный запрос: и ожидание заголовка, и
// чтение тела. Отмена уходит в апстрим вместе с контекстом запроса, то есть
// сервер перестает тратить ресурс на клиента, который уже ушёл.
func WithDeadline(next http.Handler, budget time.Duration) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ctx, cancel := context.WithTimeout(r.Context(), budget)
		defer cancel()
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}
```

## Граница тела и обрыв клиента

```go
// Package apiguard — границы запроса: размер тела, таймауты сервера, уход клиента.
package apiguard

import (
	"context"
	"errors"
	"io"
	"net/http"
	"time"
)

const maxBody = 8 << 20 // 8 МиБ

// BodyLimit ограничивает тело до разбора. Без него «небольшой JSON» от клиента —
// это 10 ГиБ в памяти: json.Decoder читает, пока его не прижмёт OOM-killer.
// Обрезанное чтение даёт ErrHandlerTimeout/«request body too large» на стороне
// http.Server, а не панику в разборе.
func BodyLimit(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.ContentLength > maxBody {
			http.Error(w, "слишком большое тело запроса", http.StatusRequestEntityTooLarge)
			return
		}
		r.Body = http.MaxBytesReader(w, r.Body, maxBody)
		next.ServeHTTP(w, r)
	})
}

// ServerTimeouts — обязательный набор. ReadHeaderTimeout закрывает медлительных
// клиентов (Slowloris); Read/WriteTimeout ломают длинные загрузки и стриминг,
// поэтому их ставят осознанно или не ставят вовсе.
func ServerTimeouts(s *http.Server) {
	s.ReadHeaderTimeout = 10 * time.Second
	s.IdleTimeout = 120 * time.Second
}

// ClientGone сообщает, что читающий уже ушёл: проверять имеет смысл перед
// дорогой операцией и обязательно перед записью ответа.
func ClientGone(ctx context.Context) bool { return ctx.Err() != nil }

// Stream пробрасывает поток, проверяя отмену между частями. Игнорировать err от
// w.Write нельзя: оборванный клиент остаётся «живым» для сервера, и цикл читает
// апстрим до его конца.
func Stream(ctx context.Context, w io.Writer, src io.Reader) error {
	buf := make([]byte, 32*1024)
	for {
		if err := ctx.Err(); err != nil {
			return err
		}
		n, rerr := src.Read(buf)
		if n > 0 {
			if _, werr := w.Write(buf[:n]); werr != nil {
				return werr
			}
			if f, ok := w.(http.Flusher); ok {
				f.Flush()
			}
		}
		if rerr != nil {
			if errors.Is(rerr, io.EOF) {
				return nil
			}
			return rerr
		}
	}
}
```

## Какие коды означает отказ апстрима

| Что случилось | Код | Можно повторять? |
|---|---|---|
| Соединение не установлено, хост не отвечает | 503 Service Unavailable | да, с backoff |
| Апстрим принял запрос, не ответил за бюджет | 504 Gateway Timeout | только если запрос идемпотентен |
| Апстрим ответил битым HTTP / сбросил посреди ответа | 502 Bad Gateway | идемпотентный — да |
| Клиент ушёл (context.Canceled) | ничего не пишем | — |
| Прокси сам упал на своей логике | 500 Internal Server Error | нет |

Различение 502/503/504 — не педантизм: клиент с ретраем по 503 и без ретрая по 504 ведёт себя по-разному, и на «везде 500» обе ветки превращаются в шторм повторных запросов. Повтор — по правилам [http-client.md](http-client.md) (бюджет, `Retry-After`), а не «ещё три раза».

## Практика

- `http.TimeoutHandler` оборачивает обработчик и отдаёт 500 по истечении, но **не отменяет** работу внутри: запрос в апстрим живёт дальше и держит соединение. Нужна настоящая отмена — контекст запроса ([context.md](context.md)).
- Таймауты сервера и клиента независимы: `http.Client{Timeout: ...}` в клиенте не мешает вашему серверу держать соединение вечно. Границы ставят с обеих сторон.
- Задержка прокси должна быть видна: `Duration` histogram на маршрут с лейблом апстрима ([metrics.md](metrics.md)) — иначе «тормозит» обсуждается без чисел.
- `X-Forwarded-For` доверять только известному фронту: список доверенных сетей — в конфигурации, иначе адрес себе допишет любой, кто попросит.
- Дедлайн, приехавший извне (`X-Request-Deadline`), надо обрезать до своего бюджета, иначе клиент может попросить «ждать час».
- Буферизация тела в прокси — отдельный риск: `ReverseProxy` тело не буферизует, а вот любой ваш `io.ReadAll(r.Body)` перед пробросом — буферизует.

## Related

- [http-client.md](http-client.md) — транспорт, ретраи, `Retry-After`
- [http-server.md](http-server.md) — таймауты сервера, `MaxHeaderBytes`, корректное завершение
- [context.md](context.md) — отмена по уходу клиента
- [metrics.md](metrics.md) — длительность и коды проксированных ответов
- [websocket.md](websocket.md) — проксирование апгрейда соединения
