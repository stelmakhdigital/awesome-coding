---
id: llm-streaming
title: "LLM: стриминг ответа — SSE из Go, простои, отмена клиента"
lang: llm
min_version: null
category: snippet
tags: [streaming, sse, llm, tokens, first-token, flush, heartbeat, cancellation, openai-compatible]
status: stable
updated: 2026-11-25
---

# Стриминг ответа: SSE из Go, простои, отмена клиента

**Когда использовать** — ответ генерируется секундами и пользователь должен видеть текст, а не спиннер: чат, объяснение кода, разбор резюме, устная речь по частям. Первый токен обычно приходит за 0,3-2 с, весь ответ — за 10-40 с: показывать его частями значит сократить ощущаемое ожидание в разы.
**Когда НЕ использовать** — короткий детерминированный ответ (классификация, извлечение полей: ждите целиком, ретраить дешевле); фоновая работа без зрителя (очередь + статус); нужен обмен в обе стороны во время генерации (отмена, «стоп», дорассказывание) — тогда WebSocket ([../../go/snippets/websocket.md](../../go/snippets/websocket.md)).

## Поток из сервера в браузер

```go
// Package sse — text/event-stream: события сервера в браузер.
package sse

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"
)

// ErrNoFlusher — ResponseWriter не умеет Flush: ответ буферизуется, и «первый
// токен мгновенно» превращается в «всё сразу в конце».
var ErrNoFlusher = errors.New("sse: ответ без поддержки Flush")

type Stream struct {
	out       io.Writer
	flush     func()
	heartbeat time.Duration
}

// Open пишет заголовки и отправляет первый байт. Вызов обязателен до долгого
// ожидания: клиент считает соединение установленным только после заголовков.
func Open(w http.ResponseWriter, heartbeat time.Duration) (*Stream, error) {
	fl, ok := w.(http.Flusher)
	if !ok {
		return nil, ErrNoFlusher
	}

	// Общий WriteTimeout сервера обрывает стрим на середине: для этого ответа
	// дедлайн записи снимаем, таймауты остаются на контексте запроса.
	rc := http.NewResponseController(w)
	if err := rc.SetWriteDeadline(time.Time{}); err != nil && !errors.Is(err, http.ErrNotSupported) {
		return nil, fmt.Errorf("sse: снять дедлайн записи: %w", err)
	}

	h := w.Header()
	h.Set("content-type", "text/event-stream; charset=utf-8")
	h.Set("cache-control", "no-cache, no-transform")
	h.Set("x-accel-buffering", "no") // nginx: не буферизовать ответ

	w.WriteHeader(http.StatusOK)
	fl.Flush()

	if heartbeat <= 0 {
		heartbeat = 15 * time.Second
	}
	return &Stream{out: w, flush: fl.Flush, heartbeat: heartbeat}, nil
}

// Send — одно событие. JSON обязан быть в одну строку: json.Marshal и даёт
// однострочник, многострочное содержимое требует префикса «data: » на каждую
// строку, и это надо делать явно, а не «как-нибудь».
func (s *Stream) Send(event string, data any) error {
	payload, err := json.Marshal(data)
	if err != nil {
		return fmt.Errorf("sse: сериализация %s: %w", event, err)
	}
	if _, err := fmt.Fprintf(s.out, "event: %s\ndata: %s\n\n", event, payload); err != nil {
		return err // клиент ушёл: это не 500, а повод остановить генерацию
	}
	s.flush()
	return nil
}

// Keepalive — комментарии-пульсы. Пока модель думает над первым токеном,
// соединение молчит, и промежуточный прокси закрывает его по своему
// read-таймауту. Пульс обязан приходить чаще этого таймаута.
func (s *Stream) Keepalive(ctx context.Context) {
	t := time.NewTicker(s.heartbeat)
	defer t.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-t.C:
			if _, err := fmt.Fprint(s.out, ": ping\n\n"); err != nil {
				return
			}
			s.flush()
		}
	}
}
```

## Чтение потока от провайдера

```go
// Package llmstream — чтение SSE от OpenAI-совместимого API и пересылка.
package llmstream

import (
	"bufio"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"
)

// ErrIdle — между чанками пауза длиннее лимита. Отдельная ветка: «модель
// молчит» лечится не так, как «соединение упало».
var ErrIdle = errors.New("llm: поток молчит")

// ErrProtocol — провайдер прислал не то, что обещал: например JSON в поле data
// не разбирается. Ретраить бессмысленно, нужен разбор.
var ErrProtocol = errors.New("llm: неожиданный формат потока")

// Sink — потребитель текста (SSE-стрим, лог, метрики).
type Sink interface {
	Send(text string) error
}

type chunk struct {
	Choices []struct {
		Delta struct {
			Content string `json:"content"`
		} `json:"delta"`
		FinishReason *string `json:"finish_reason"`
	} `json:"choices"`
}

// Relay перекачивает поток в sink и возвращает собранный текст целиком.
//
// resp должен быть получен запросом, построенным на том же ctx: отмена
// контекста прерывает чтение тела, иначе горутина сканера останется висеть.
// Тело ответа закрывает вызывающий.
func Relay(ctx context.Context, resp *http.Response, sink Sink, idle time.Duration) (string, error) {
	if idle <= 0 {
		idle = 30 * time.Second
	}

	sc := bufio.NewScanner(resp.Body)
	sc.Buffer(make([]byte, 0, 64*1024), 1<<20) // строки SSE бывают длинными

	lines := make(chan string)
	go func() {
		defer close(lines)
		for sc.Scan() {
			select {
			case lines <- sc.Text():
			case <-ctx.Done():
				return
			}
		}
	}()

	var full strings.Builder
	timer := time.NewTimer(idle)
	defer timer.Stop()

	for {
		select {
		case <-ctx.Done():
			return full.String(), ctx.Err()
		case <-timer.C:
			return full.String(), fmt.Errorf("%w после %s", ErrIdle, idle)
		case line, ok := <-lines:
			if !ok {
				if err := sc.Err(); err != nil {
					return full.String(), fmt.Errorf("llm: чтение потока: %w", err)
				}
				return full.String(), nil
			}
			timer.Reset(idle)

			text, stop, err := parseLine(line)
			if err != nil {
				return full.String(), err
			}
			if text != "" {
				full.WriteString(text)
				if err := sink.Send(text); err != nil {
					return full.String(), err
				}
			}
			if stop {
				return full.String(), nil
			}
		}
	}
}

// parseLine — одна строка потока. Комментарий, пустая строка и «event:» — не
// данные: их игнорирование должно быть явным, иначе первое же «: keepalive»
// от провайдера разбивается об json.Unmarshal.
func parseLine(line string) (text string, stop bool, err error) {
	line = strings.TrimRight(line, "\r")

	switch {
	case line == "" || strings.HasPrefix(line, ":"):
		return "", false, nil
	case strings.HasPrefix(line, "event:"), strings.HasPrefix(line, "id:"), strings.HasPrefix(line, "retry:"):
		return "", false, nil
	case !strings.HasPrefix(line, "data:"):
		return "", false, fmt.Errorf("%w: %q", ErrProtocol, line)
	}

	data := strings.TrimSpace(strings.TrimPrefix(line, "data:"))
	if data == "[DONE]" {
		return "", true, nil
	}

	var c chunk
	if err := json.Unmarshal([]byte(data), &c); err != nil {
		return "", false, fmt.Errorf("%w: %v", ErrProtocol, err)
	}
	for _, ch := range c.Choices {
		if ch.Delta.Content != "" {
			text += ch.Delta.Content
		}
		if ch.FinishReason != nil && *ch.FinishReason != "" {
			stop = true
		}
	}
	return text, stop, nil
}
```

## Как это собирается

```go
// Package handler — сборка: заголовки, пульс, пересылка, терминальное событие.
package handler

import (
	"context"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"time"

	"example.com/ac/llmstream"
	"example.com/ac/sse"
)

// ChatModel — провайдер, отвечающий SSE-потоком. Клиент обязан строить запрос
// на переданном контексте: отмена обязана доходить до чтения тела.
type ChatModel interface {
	StreamChat(ctx context.Context, body io.Reader) (*http.Response, error)
}

type Config struct {
	IdleTimeout time.Duration
}

type Handler struct {
	llm ChatModel
	cfg Config
	log *slog.Logger
}

// Chat — SSE-эндпоинт генерации.
func (h *Handler) Chat(w http.ResponseWriter, r *http.Request) {
	stream, err := sse.Open(w, 15*time.Second)
	if err != nil {
		http.Error(w, err.Error(), http.StatusServiceUnavailable)
		return
	}

	ctx, cancel := context.WithCancel(r.Context())
	defer cancel()

	go stream.Keepalive(ctx)

	resp, err := h.llm.StreamChat(ctx, r.Body)
	if err != nil {
		h.log.Error("запрос к модели", "err", err)
		_ = stream.Send("error", map[string]string{"message": "модель недоступна"})
		return
	}
	defer resp.Body.Close()

	text, err := llmstream.Relay(ctx, resp, sseSink{stream: stream}, h.cfg.IdleTimeout)
	h.log.Info("стрим завершён", "symbols", len(text), "err", err)

	switch {
	case err == nil:
		_ = stream.Send("done", map[string]any{"ok": true})
	case errors.Is(err, context.Canceled):
		// Клиент закрыл вкладку: генерацию остановили, это не инцидент.
		h.log.Info("клиент отключился")
	default:
		h.log.Warn("стрим прерван", "err", err)
		_ = stream.Send("error", map[string]string{"message": "поток прерван"})
	}
}

// sseSink — адаптер: текст чанка уходит событием token.
type sseSink struct{ stream *sse.Stream }

func (x sseSink) Send(text string) error {
	return x.stream.Send("token", map[string]string{"t": text})
}
```

## Что решает исход

| Событие | Что видит пользователь | Что делать |
|---|---|---|
| Клиент закрыл вкладку (`context.Canceled`) | ничего | остановить генерацию: продолжение — оплаченные токены в пустоту |
| Прокси закрыл молчаливое соединение | текст оборвался | heartbeat чаще таймаута прокси; на nginx — `proxy_read_timeout`, `X-Accel-Buffering: no` |
| Провайдер молчит (`ErrIdle`) | курсор мигает | оборвать и показать собранное; повтор — только если ответ ещё не начался |
| Ответ начался и упал | половина текста | **не повторять запрос**: повтор даст другой текст и склейку. Предложить «продолжить с этого места» отдельным запросом с уже написанным в контексте |
| Буферизация по пути | всё вывалилось в конце | проверить `Flush`, `x-accel-buffering`, сжатие (`no-transform`), прокси-буферы |

## Метрики стрима

Без них «тормозит» не обсудить: время до первого токена (TTFT), длительность всего ответа, число прерванных потоков по причине, средняя длина. TTFT и полная длительность — разные метрики: первая объясняет «почему он молчит», вторая — «почему так долго» ([../../go/snippets/metrics.md](../../go/snippets/metrics.md)).

На стороне браузера `EventSource` умеет только GET без тела — для POST-запроса с телом читают `fetch`-ответ через `ReadableStream` и `TextDecoder`, разбирая строки сами; переподключение и «догнать пропущенное» тогда тоже на стороне клиента ([../../react/snippets/effects.md](../../react/snippets/effects.md)).

## Related

- [retries-budget.md](retries-budget.md) — бюджет повторов: стрим повторяется иначе, чем обычный запрос
- [structured-output.md](structured-output.md) — структурированный ответ со стримингом не дружит: JSON по частям не разбирается
- [../../go/snippets/websocket.md](../../go/snippets/websocket.md) — двусторонний канал, если нужен «стоп» и дорассказ
- [../../go/snippets/proxy.md](../../go/snippets/proxy.md) — `FlushInterval`, границы времени, коды 502/504
- [../../go/snippets/metrics.md](../../go/snippets/metrics.md) — TTFT и длительность как отдельные метрики
- [../rules.md](../rules.md) — правила раздела: таймауты, бюджеты, что не стоит повторять
