---
id: go-websocket
title: "Go: WebSocket — handshake, медленные клиенты, переподключение"
lang: go
min_version: "1.22"
category: snippet
tags: [websocket, ws, http, upgrade, origin, ping, backpressure, reconnect, coder-websocket]
status: stable
updated: 2026-11-25
---

# WebSocket: handshake, медленные клиенты, переподключение

**Когда использовать** — сервер сам что-то сообщает клиенту (стадии задачи, чат, присутствие, прогресс долгого job), и опросом это делается с лагом в секунду и лишней нагрузкой. Библиотека — `github.com/coder/websocket` v1.8 (продолжение `nhooyr.io/websocket`: контексты в каждом вызове, конкурентные записи, никаких глобальных хабов).
**Когда НЕ использовать** — однонаправленный поток событий хватит и SSE (`text/event-stream`, переподключение встроенное, прокси дружелюбнее); запрос-ответ — обычный HTTP с таймаутом; стрим внутри сервисов — gRPC ([grpc.md](grpc.md)). Держать WebSocket «на всякий случай» там, где данные меняются раз в минуту, — это ещё и состояние соединения в каждом поде.

## Handshake, чтение, запись

```go
// Package ws — соединение: handshake с проверкой Origin, отдельные чтение и
// запись, лимит размера сообщения.
package ws

import (
	"context"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"time"

	"github.com/coder/websocket"
)

// OriginPatterns — белый список источников браузера. Библиотека проверяет Origin
// сама: без списка соединение из браузера не поднимется, а InsecureSkipVerify
// открывает его для любого сайта. Строки с маской — «localhost:*».
var upgrader = &websocket.AcceptOptions{
	OriginPatterns: []string{"localhost:5173", "app.example.com"},
	Subprotocols:   []string{"json"},
}

// Hub — куда уходят входящие сообщения и откуда берутся исходящие.
type Hub interface {
	Join(send chan<- []byte)
	Leave(send chan<- []byte)
	Publish(payload []byte) int
}

// Handle держит соединение, пока жива хотя бы одна сторона.
func Handle(hub Hub, log *slog.Logger) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		conn, err := websocket.Accept(w, r, upgrader)
		if err != nil {
			// Ответ (403/400) уже написан внутри Accept: второй записи не будет.
			log.Error("websocket handshake", "err", err, "origin", r.Header.Get("Origin"))
			return
		}
		defer conn.CloseNow() // страховка: штатный Close может не состояться

		// r.Context() умирает вместе с обработчиком. Писателю, который живёт
		// отдельной горутиной, нужен несвязанный с запросом контекст.
		ctx := r.Context()
		wctx, cancelWriter := context.WithCancel(context.Background())
		defer cancelWriter()

		send := make(chan []byte, 8)
		hub.Join(send)
		defer hub.Leave(send)

		// Без лимита кадр в 100 МБ = 100 МБ на соединение: один клиент выкачивает
		// память процесса. Превышение лимита библиотека сама закрывает соединение.
		conn.SetReadLimit(1 << 20)

		errc := make(chan error, 1)
		go func() { errc <- writeLoop(wctx, conn, send, log) }()

		for {
			typ, payload, err := conn.Read(ctx)
			if err != nil {
				break
			}
			if typ != websocket.MessageText && typ != websocket.MessageBinary {
				_ = conn.Close(websocket.StatusUnsupportedData, "ожидается текст или бинарный кадр")
				break
			}
			hub.Publish(payload)
		}

		cancelWriter()
		<-errc
		// Код закрытия видит клиент. «1006» (оборвано без кода) — самый частый
		// вопрос «почему клиент переподключается бесконечно».
		_ = conn.Close(websocket.StatusNormalClosure, "")
	}
}

// writeLoop — единственный писатель соединения: порядок сообщений сохраняется,
// ping не спорит с очередью за запись.
func writeLoop(ctx context.Context, conn *websocket.Conn, send <-chan []byte, log *slog.Logger) error {
	const (
		pingEvery   = 25 * time.Second
		writeBudget = 10 * time.Second
	)

	ticker := time.NewTicker(pingEvery)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			pctx, cancel := context.WithTimeout(ctx, writeBudget)
			err := conn.Ping(pctx)
			cancel()
			if err != nil {
				log.Debug("websocket ping", "err", err)
				return err
			}
		case payload, ok := <-send:
			if !ok {
				return nil
			}
			wctx, cancel := context.WithTimeout(ctx, writeBudget)
			err := conn.Write(wctx, websocket.MessageText, payload)
			cancel()
			if err != nil {
				log.Debug("websocket write", "err", err)
				return err
			}
		}
	}
}

// Encode — тело сообщения. Ошибка маршалинга означает «соединение закрываем»:
// в очередь нельзя класть пустой кадр, клиент примет его как валидное сообщение.
func Encode(v any) ([]byte, error) {
	payload, err := json.Marshal(v)
	if err != nil {
		return nil, errors.Join(errors.New("websocket: encode"), err)
	}
	return payload, nil
}
```

## Рассылка и медленный клиент

```go
// Package hub — рассылка: кто не успел принять сообщение, тот отключается.
package hub

import (
	"sync"

	"example.com/ac/ws"
)

// Проверка контракта на этапе сборки: подпись хаба разъедётся с обработчиком не
// в момент первого сообщения, а в CI.
var _ ws.Hub = (*Hub)(nil)

// Клиенты хранятся как send-only каналы: close на таком разрешён, а отправить в
// чужой канал из хаба, кроме Publish, не получится.
type Hub struct {
	mu      sync.Mutex
	clients map[chan<- []byte]struct{}
	dropped int
}

func New() *Hub {
	return &Hub{clients: make(map[chan<- []byte]struct{})}
}

func (h *Hub) Join(send chan<- []byte) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.clients[send] = struct{}{}
}

// Leave закрывает канал: writer-loop увидит закрытие и завершится сам.
func (h *Hub) Leave(send chan<- []byte) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if _, ok := h.clients[send]; ok {
		delete(h.clients, send)
		close(send)
	}
}

// Publish — non-blocking отправка каждому. Буфер без политики роста = «растёт до
// OOM, когда клиент уснул с телефоном в кармане». Возвращает число получателей:
// метрика «до кого дошло» честная только так.
func (h *Hub) Publish(payload []byte) int {
	h.mu.Lock()
	defer h.mu.Unlock()

	sent := 0
	for send := range h.clients {
		select {
		case send <- payload:
			sent++
		default:
			delete(h.clients, send)
			close(send) // соединение закроется с кодом; клиент переподключится
			h.dropped++
		}
	}
	return sent
}

// Stats — сколько клиентов отключено из-за медленности: метрика, а не догадка.
func (h *Hub) Stats() (clients, dropped int) {
	h.mu.Lock()
	defer h.mu.Unlock()
	return len(h.clients), h.dropped
}
```

## Клиент с переподключением

```go
// Package wsdial — клиент: backoff с джиттером и лимит подряд неудачных попыток.
package wsdial

import (
	"context"
	"errors"
	"fmt"
	"math/rand/v2"
	"net/http"
	"time"

	"github.com/coder/websocket"
)

// Run держит соединение, пока жив ctx. onMessage вызывается из этой горутины;
// ошибка из неё закрывает соединение и считается причиной переподключения.
func Run(ctx context.Context, url string, header http.Header, onMessage func([]byte) error) error {
	const (
		startBackoff = 250 * time.Millisecond
		maxBackoff   = 30 * time.Second
		maxAttempts  = 20
	)

	backoff := startBackoff
	for attempts := 0; ctx.Err() == nil; {
		err := once(ctx, url, header, onMessage)
		if ctx.Err() != nil {
			return ctx.Err()
		}
		attempts++
		if attempts >= maxAttempts {
			return fmt.Errorf("websocket: %d попыток подряд: %w", attempts, err)
		}

		sleep := backoff/2 + time.Duration(rand.Int64N(int64(backoff/2)+1))
		backoff = min(backoff*2, maxBackoff)
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(sleep):
		}
	}
	return ctx.Err()
}

func once(ctx context.Context, url string, header http.Header, onMessage func([]byte) error) error {
	conn, resp, err := websocket.Dial(ctx, url, &websocket.DialOptions{
		Subprotocols: []string{"json"},
		HTTPHeader:   header,
	})
	if err != nil {
		return fmt.Errorf("websocket dial: %w", err)
	}
	if resp != nil && resp.Body != nil {
		defer resp.Body.Close()
	}
	defer conn.CloseNow()

	conn.SetReadLimit(1 << 20)
	for {
		_, payload, err := conn.Read(ctx)
		if err != nil {
			var closeErr websocket.CloseError
			if errors.As(err, &closeErr) {
				return fmt.Errorf("websocket closed: code=%d reason=%q: %w", closeErr.Code, closeErr.Reason, err)
			}
			return err
		}
		if err := onMessage(payload); err != nil {
			_ = conn.Close(websocket.StatusInternalError, "ошибка обработчика")
			return err
		}
	}
}
```

## Что решает исход соединения

| Симптом | Причина | Что делать |
|---|---|---|
| В браузере 403, из curl работает | Origin не в `OriginPatterns`. Dev-сервер Vite шлёт `Origin: localhost:5173` через свой proxy | добавить порт в белый список; `InsecureSkipVerify` — только в локальном конфиге, и он должен быть виден в `git grep` |
| Обрывается ровно через 60 с | промежуточный прокси не видит трафика.nginx `proxy_read_timeout`, облачный балансировщик | ping чаще таймаута прокси (25 s — типовой запас), на Caddy/Nginx — `proxy_read_timeout` и `Connection: upgrade` |
| `1006` без кода | соединение убито извне: прокси, таймаут записи, OOM-killer | сервер обязан уметь закрыть с кодом; на клиенте — отличать «закрыто сервером» (`CloseError`) от «сеть пропала» |
| Клиент получает сообщения с опозданием в минуты | буфер рассылки растёт, а не переполняется | non-blocking отправка + закрытие отставшего ([hub выше](#рассылка-и-медленный-клиент)) |
| После деплоя клиенты молчат | старые соединения держат старый под, новый трафик уходит новым | при остановке — `Close(StatusGoingAway)` всем соединениям и graceful shutdown ([graceful-shutdown.md](graceful-shutdown.md)) |

## Практика

- Авторизация. Handshake-запрос приходит с куками браузера — `SameSite=Lax` их не отдаёт на кросс-домен, а токен в query попадает в логи прокси. Рабочие варианты: токен в `Sec-WebSocket-Protocol` или короткий одноразовый билет в URL, обмениваемый сразу после поднятия.
- Порядок и повтор. Переподключение означает «часть сообщений потеряна»: держите монотонный `seq` в теле сообщения и просите догонять (`since=1234`) после reconnect. Иначе клиент показывает устаревшее состояние как актуальное.
- Один хаб в памяти процесса работает ровно на один под. На нескольких подах нужен fan-out в брокере ([../messaging/snippets/rabbitmq.md](../../messaging/snippets/rabbitmq.md), Redis pub/sub в [../database/snippets/redis.md](../../database/snippets/redis.md)) и липкие сессии на балансировщике.
- Тест не требует сети: `httptest.NewServer` + `websocket.Dial` в одном процессе, схема в [testing.md](testing.md). Так проверяются и Origin-отказ, и закрытие отставшего клиента.
- Метрики соединения: активные соединения (gauge с инкрементом после `Accept`), `dropped` из хаба, ошибки handshake по Origin. Без них «отваливается» превращается в разговор без чисел ([metrics.md](metrics.md)).

## Related

- [http-server.md](http-server.md) — маршрутизатор, таймауты сервера, `http.ResponseController`
- [graceful-shutdown.md](graceful-shutdown.md) — закрыть соединения до выхода процесса
- [rate-limit.md](rate-limit.md) — лимит на handshake: он дороже обычного запроса
- [metrics.md](metrics.md) — метрики активных соединений и отключённых клиентов
- [../react/snippets/effects.md](../../react/snippets/effects.md) — читатель на стороне браузера: cleanup и переподключение
