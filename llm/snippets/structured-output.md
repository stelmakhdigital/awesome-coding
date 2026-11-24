---
id: llm-structured-output
title: "LLM: вызов со схемой ответа, ретраями и бюджетом (Go)"
lang: llm
min_version: "1.22"
category: snippet
tags: [llm, http, json-schema, retry, budget, go]
status: stable
updated: 2026-11-24
---

# Вызов модели со схемой и бюджетом (Go)

**Когда использовать** — ответ модели идёт в код: извлечение полей, классификация,
маршрутизация. Свой HTTP-слой вместо SDK: ретраи, бюджет и разбор ответа остаются
вашими, и их можно тестировать без провайдера.
**Когда НЕ использовать** — стриминг в UI (там другой цикл: накопление чанков и
отмена по закрытию клиента, см. [../decisions.md](../decisions.md)); распределённый
учёт затрат (нужен внешний счётчик, а не память процесса).

## Код

```go
// Package llmclient — вызов chat-completions-совместимого API со схемой,
// ретраями и бюджетом. Только stdlib: транспорт и деньги под нашим контролем.
package llmclient

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"math/rand/v2"
	"net/http"
	"strconv"
	"sync"
	"time"
)

// ErrSchema — ответ не разбирается по схеме. Повтор того же запроса обычно
// бесполезен: правьте промпт или схему.
var ErrSchema = errors.New("llm: response does not match schema")

// ErrBudget — остаток бюджета меньше прогнозируемой стоимости запроса.
var ErrBudget = errors.New("llm: budget exceeded")

// Message — один элемент разговора. Роль — «system» | «user» | «assistant».
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// Price — цена за миллион токенов, отдельно вход и выход.
type Price struct {
	InPer1M, OutPer1M float64
}

// Budget — остаток денег на процесс. Считаем по usage ответа, не «на глаз».
type Budget struct {
	mu      sync.Mutex
	leftUSD float64
}

func NewBudget(usd float64) *Budget { return &Budget{leftUSD: usd} }

// Charge списывает стоимость; отрицательный остаток — это превышение,
// и оно видно в ErrBudget следующих запросов.
func (b *Budget) Charge(costUSD float64) {
	b.mu.Lock()
	b.leftUSD -= costUSD
	b.mu.Unlock()
}

func (b *Budget) Remaining() float64 {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.leftUSD
}

// Client — тонкий клиент поверх HTTP. BaseURL позволяет подменить провайдера
// (включая локальный сервер) без правок вызывающего кода.
type Client struct {
	BaseURL string
	APIKey  string
	Model   string
	HTTP    *http.Client
	Price   Price
	Budget  *Budget
	Log     *slog.Logger
}

// New: timeout — на весь запрос, включая ретраи: дедлайн ctx вызывающего всё
// ограничивает строже.
func New(baseURL, apiKey, model string, price Price, budget *Budget) *Client {
	return &Client{
		BaseURL: baseURL, APIKey: apiKey, Model: model, Price: price, Budget: budget,
		HTTP: &http.Client{Timeout: 60 * time.Second},
		Log:  slog.Default(),
	}
}

type chatRequest struct {
	Model     string    `json:"model"`
	Messages  []Message `json:"messages"`
	MaxTokens int       `json:"max_tokens,omitempty"`
	Temp      float64   `json:"temperature"`
	// JSON-режим ответа, если провайдер его поддерживает.
	ResponseFormat *struct {
		Type string `json:"type"`
	} `json:"response_format,omitempty"`
}

type chatResponse struct {
	Choices []struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
		FinishReason string `json:"finish_reason"`
	} `json:"choices"`
	Usage struct {
		PromptTokens     int `json:"prompt_tokens"`
		CompletionTokens int `json:"completion_tokens"`
	} `json:"usage"`
	Error *struct {
		Message string `json:"message"`
	} `json:"error"`
}

// Estimate — прогноз стоимости по числу входных символов и лимиту ответа.
// Худший случай: пока usage нет, платим по максимуму.
func (c *Client) Estimate(inChars, maxOutTokens int) float64 {
	inTokens := float64(inChars) / 4
	return (inTokens*float64(c.Price.InPer1M) + float64(maxOutTokens)*c.Price.OutPer1M) / 1e6
}

func (c *Client) cost(inTokens, outTokens int) float64 {
	return (float64(inTokens)*c.Price.InPer1M + float64(outTokens)*c.Price.OutPer1M) / 1e6
}

// Complete отправляет запрос и расписывает content по схеме в out.
// attempts — всего попыток (не «повторов сверх»): ретрай стоит денег и времени.
func (c *Client) Complete(ctx context.Context, msgs []Message, maxTokens, attempts int, out any) error {
	body := chatRequest{Model: c.Model, Messages: msgs, MaxTokens: maxTokens, Temp: 0}
	body.ResponseFormat = &struct {
		Type string `json:"type"`
	}{Type: "json_object"}

	payload, err := json.Marshal(body)
	if err != nil {
		return fmt.Errorf("llm: marshal: %w", err)
	}
	// Грубая, но консервативная оценка входа — до отправки, а не после счёта.
	inChars := 0
	for _, m := range msgs {
		inChars += len(m.Content)
	}
	if c.Budget != nil && c.Budget.Remaining() < c.Estimate(inChars, maxTokens) {
		return ErrBudget
	}

	var lastErr error
	for attempt := 0; attempt < attempts; attempt++ {
		if attempt > 0 {
			if err := sleepBackoff(ctx, attempt); err != nil {
				return err
			}
		}
		usage, content, retryAfter, err := c.callOnce(ctx, payload)
		if err == nil {
			if c.Budget != nil {
				c.Budget.Charge(c.cost(usage[0], usage[1]))
			}
			c.Log.Info("llm call", "model", c.Model, "in", usage[0], "out", usage[1],
				"attempt", attempt+1)
			if e := json.Unmarshal([]byte(content), out); e != nil {
				return fmt.Errorf("%w: %v", ErrSchema, e)
			}
			return nil
		}
		lastErr = err
		if retryAfter > 0 {
			if e := waitCtx(ctx, retryAfter); e != nil {
				return e
			}
		}
	}
	return fmt.Errorf("llm: %d попыток: %w", attempts, lastErr)
}

// callOnce — один HTTP-обмен. Возвращает retryAfter > 0, когда провайдер сам
// сказал, сколько ждать (429/503), и это важнее нашего backoff.
func (c *Client) callOnce(ctx context.Context, payload []byte) (usage [2]int, content string, retryAfter time.Duration, err error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.BaseURL+"/chat/completions",
		bytes.NewReader(payload))
	if err != nil {
		return usage, "", 0, err
	}
	req.Header.Set("content-type", "application/json")
	req.Header.Set("authorization", "Bearer "+c.APIKey)

	resp, err := c.HTTP.Do(req)
	if err != nil {
		return usage, "", 0, err // сеть/дедлайн — retryable
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(io.LimitReader(resp.Body, 4<<20)) // лимит: ответ не безразмерный
	if err != nil {
		return usage, "", 0, err
	}
	if resp.StatusCode == http.StatusTooManyRequests || resp.StatusCode >= 500 {
		return usage, "", retryAfterOf(resp), fmt.Errorf("llm: http %d", resp.StatusCode)
	}
	if resp.StatusCode != http.StatusOK {
		// 4xx по смыслу — битый запрос или доступ: не ретраить.
		return usage, "", 0, fmt.Errorf("llm: http %d: %s", resp.StatusCode, trim(string(data)))
	}

	var parsed chatResponse
	if err := json.Unmarshal(data, &parsed); err != nil {
		return usage, "", 0, fmt.Errorf("llm: decode: %w", err)
	}
	if parsed.Error != nil {
		return usage, "", 0, fmt.Errorf("llm: api: %s", parsed.Error.Message)
	}
	if len(parsed.Choices) == 0 {
		return usage, "", 0, errors.New("llm: пустой ответ (no choices)")
	}
	usage = [2]int{parsed.Usage.PromptTokens, parsed.Usage.CompletionTokens}
	return usage, parsed.Choices[0].Message.Content, 0, nil
}

func retryAfterOf(resp *http.Response) time.Duration {
	v := resp.Header.Get("retry-after")
	if v == "" {
		return 0
	}
	if secs, err := strconv.Atoi(v); err == nil && secs > 0 {
		return time.Duration(secs) * time.Second
	}
	return 0
}

// sleepBackoff — экспоненциальная задержка с jitter, прерываемая ctx.
func sleepBackoff(ctx context.Context, attempt int) error {
	base := time.Duration(1<<uint(attempt)) * 500 * time.Millisecond
	return waitCtx(ctx, base+time.Duration(rand.Int64N(int64(base/2+1))))
}

func waitCtx(ctx context.Context, d time.Duration) error {
	t := time.NewTimer(d)
	defer t.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-t.C:
		return nil
	}
}

func trim(s string) string {
	if len(s) > 200 {
		return s[:200] + "…"
	}
	return s
}
```

## Pitfalls

- `response_format` поддерживают не все эндпоинты: при `unknown field` уберите поле —
  разбор по схеме всё равно обязателен, это он защищает код.
- Оценка входа через `len/4` — порядок величины, не tokenizer. Для бюджета «в ноль»
  считайте токены токенизатором провайдера или держите запас.
- Ретраи вне ctx: без `waitCtx` сон переживёт отмену запроса, и воркер останется
  занятым на минуту после того, как клиент ушёл.
- `usage` отсутствует у части ответов (особенно в кэшируемых/пакетных режимах):
  ноль в метрике — не «бесплатно», а «не посчитано»; учитывайте по максимуму.
- Ответ не по схеме — не повод ретраить в том же промпте: это правка промпта/схемы
  и регресс-кейс в [../evals.md](../evals.md).
- Ключ в заголовке — значит HTTPS обязателен; `BaseURL` из конфигурации должен быть
  вашим собственным (allowlist), иначе запрос с ключом уходит на чужой хост.

## Related

- [../rules.md](../rules.md) — что обязано быть в вызове
- [retries-budget.md](retries-budget.md) — тот же слой на Python, с кэшем
- [../../go/snippets/http-client.md](../../go/snippets/http-client.md) — транспорт в Go
- [../../shared/authentication.md](../../shared/authentication.md) — секреты и заголовки
