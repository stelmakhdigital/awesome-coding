---
id: llm-tool-calls
title: "LLM: вызовы с инструментами — цикл, бюджет, резервная модель"
lang: llm
min_version: null
category: snippet
tags: [tool-calling, function-calling, agents, tool-loop, budget, fallback, openai-compatible, json-schema]
status: stable
updated: 2026-11-24
proof: "SelfCheck на httptest выполнен go run в golang:1.27-alpine 2026-11-24: лента ответов, бюджет раундов и ловля цикла проверены без сети"
---

# Вызовы с инструментами: цикл, бюджет, резервная модель

**Когда использовать** — модель сама решает, что вызвать: поиск по базе знаний, внутренний API, пересчёт, маршрутизация запроса. Ответ зависит от данных, которых нет в промпте, и их надо достать посреди разговора.
**Когда НЕ использовать** — операция одна и известна заранее (это вызов со схемой, а не инструменты: [structured-output.md](structured-output.md)); у инструмента необратимый эффект (списать деньги, удалить, отправить письмо) — такой вызов требует подтверждения человеком, и никакая схема его не заменяет; бюджет на прогон не определён — цикл без границ это счёт, а не фича.

## Формат, на котором всё держится

```go
// Package agent — вызов модели с инструментами: формат, реестр, цикл с бюджетом.
package agent

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// Message — сообщение ленты. Два поля, которые чаще всего теряют: ToolCallID у
// результата (без него провайдер не сопоставит ответ с вызовом) и то, что
// arguments — строка с JSON, а не объект.
type Message struct {
	Role       string     `json:"role"`
	Content    string     `json:"content,omitempty"`
	ToolCallID string     `json:"tool_call_id,omitempty"`
	ToolCalls  []ToolCall `json:"tool_calls,omitempty"`
}

type ToolCall struct {
	ID       string       `json:"id"`
	Type     string       `json:"type"`
	Function FunctionCall `json:"function"`
}

type FunctionCall struct {
	Name      string `json:"name"`
	Arguments string `json:"arguments"` // JSON в строке, не объект
}

// ToolSpec — описание инструмента. Parameters — JSON schema: по ней модель
// формирует arguments, и по ней же обязаны проверять пришедшее.
type ToolSpec struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	Parameters  map[string]any `json:"parameters"`
}

type request struct {
	Model       string     `json:"model"`
	Messages    []Message  `json:"messages"`
	Tools       []toolWire `json:"tools,omitempty"`
	ToolChoice  string     `json:"tool_choice,omitempty"`
	MaxTokens   int        `json:"max_tokens,omitempty"`
	Temperature float64    `json:"temperature,omitempty"`
}

type toolWire struct {
	Type     string   `json:"type"`
	Function ToolSpec `json:"function"`
}

type response struct {
	Choices []struct {
		Message      Message `json:"message"`
		FinishReason string  `json:"finish_reason"`
	} `json:"choices"`
	Usage struct {
		PromptTokens     int `json:"prompt_tokens"`
		CompletionTokens int `json:"completion_tokens"`
		TotalTokens      int `json:"total_tokens"`
	} `json:"usage"`
	Error *struct {
		Message string `json:"message"`
		Type    string `json:"type"`
	} `json:"error,omitempty"`
}

// Client — chat-completions-совместимый вызов (провайдер или локальный сервер).
type Client struct {
	http *http.Client
	base string
	key  string
}

func NewClient(base, key string, timeout time.Duration) *Client {
	return &Client{http: &http.Client{Timeout: timeout}, base: base, key: key}
}

// Chat — один round-trip. Стриминг здесь не используется: аргументы инструмента
// по частям не разбираются, а ретрай стрима даёт дубли текста.
func (c *Client) Chat(ctx context.Context, model string, msgs []Message, tools []ToolSpec, maxTokens int) (*response, error) {
	req := request{Model: model, Messages: msgs, MaxTokens: maxTokens, ToolChoice: "auto"}
	for _, t := range tools {
		req.Tools = append(req.Tools, toolWire{Type: "function", Function: t})
	}

	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("agent: собрать запрос: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.base+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("content-type", "application/json")
	httpReq.Header.Set("authorization", "Bearer "+c.key)

	httpResp, err := c.http.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("agent: запрос %s: %w", model, err)
	}
	defer httpResp.Body.Close()

	// Ответ читается с пределом: «модель» может оказаться шлюзом, отдающим
	// страницу ошибки на мегабайты.
	raw, err := io.ReadAll(io.LimitReader(httpResp.Body, 8<<20))
	if err != nil {
		return nil, fmt.Errorf("agent: прочитать ответ: %w", err)
	}
	if httpResp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("agent: %s: %s: %s", model, httpResp.Status, snippet(raw))
	}

	var resp response
	if err := json.Unmarshal(raw, &resp); err != nil {
		return nil, fmt.Errorf("agent: разбор ответа %s: %w", model, err)
	}
	if resp.Error != nil {
		return nil, fmt.Errorf("agent: %s: %s", model, resp.Error.Message)
	}
	if len(resp.Choices) == 0 {
		return nil, fmt.Errorf("agent: %s: пустой choices", model)
	}
	return &resp, nil
}

// snippet — кусок тела в сообщение об ошибке: без него разбор начинается с
// повторного запроса.
func snippet(b []byte) string {
	const max = 200
	if len(b) <= max {
		return string(b)
	}
	return string(b[:max]) + "…"
}
```

## Реестр инструментов

```go
package agent

import (
	"context"
	"encoding/json"
	"fmt"
	"time"
)

// Tool — исполняемый инструмент. Аргументы приходят разобранными: кривой JSON
// в arguments у моделей случается чаще, чем принято думать.
type Tool struct {
	Spec ToolSpec
	Fn   func(ctx context.Context, args map[string]any) (string, error)

	// Timeout — на сам вызов: зависший инструмент съедает бюджет раунда и
	// держит соединение.
	Timeout time.Duration
}

type Registry struct {
	tools map[string]Tool
	names []string
}

func NewRegistry(tools ...Tool) *Registry {
	r := &Registry{tools: make(map[string]Tool, len(tools))}
	for _, t := range tools {
		r.tools[t.Spec.Name] = t
		r.names = append(r.names, t.Spec.Name)
	}
	return r
}

func (r *Registry) Specs() []ToolSpec {
	specs := make([]ToolSpec, 0, len(r.names))
	for _, n := range r.names {
		specs = append(specs, r.tools[n].Spec)
	}
	return specs
}

// Call выполняет tool_call. Ошибка отдаётся дважды: текстом для модели (она
// способна поправиться) и ошибкой для нас (чтобы не записать это в успех).
func (r *Registry) Call(ctx context.Context, call ToolCall) (string, error) {
	tool, ok := r.tools[call.Function.Name]
	if !ok {
		// Неизвестный инструмент — ответ модели, а не 500: список даёт ей шанс
		// выбрать существующий. Вызывать по имени «чтобы было» нельзя: имя
		// приходит извне.
		return fmt.Sprintf("инструмент %q неизвестен; доступны: %v", call.Function.Name, r.names),
			fmt.Errorf("agent: неизвестный инструмент %q", call.Function.Name)
	}

	args := map[string]any{}
	if call.Function.Arguments != "" {
		if err := json.Unmarshal([]byte(call.Function.Arguments), &args); err != nil {
			return fmt.Sprintf("arguments не разбираются: %v — пришли заново валидным JSON", err),
				fmt.Errorf("agent: аргументы %s: %w", tool.Spec.Name, err)
		}
	}

	timeout := tool.Timeout
	if timeout <= 0 {
		timeout = 10 * time.Second
	}
	cctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	out, err := tool.Fn(cctx, args)
	if err != nil {
		// Внутренности наружу не уходят: строки подключения и стеки модели не
		// нужны, а в лог — обязательны.
		return "инструмент завершился с ошибкой", fmt.Errorf("agent: %s: %w", tool.Spec.Name, err)
	}
	return out, nil
}
```

## Цикл с границами

```go
package agent

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"time"
)

var ErrBudget = errors.New("бюджет исчерпан")

// ErrLoop — модель второй раз подряд просит ровно то же действие. Продолжать
// бессмысленно: она будет просить это до конца бюджета.
var ErrLoop = errors.New("повтор одного и того же вызова")

// Limits — границы прогона. Раунды, токены, время: «максимум 10 раундов» без
// ограничения токенов — это счёт на сотни тысяч токенов.
type Limits struct {
	Rounds int
	Tokens int
	Wall   time.Duration
}

// Run ведёт диалог до финального ответа или до границы бюджета. models[0] —
// основная модель, остальные — резерв при отказе.
func Run(ctx context.Context, c *Client, models []string, reg *Registry, history []Message, lim Limits, maxTokens int) (string, []Message, error) {
	if len(models) == 0 {
		return "", history, errors.New("agent: модель не задана")
	}
	if lim.Rounds <= 0 {
		lim.Rounds = 6
	}
	if lim.Wall > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, lim.Wall)
		defer cancel()
	}

	msgs := append([]Message(nil), history...)
	spent := 0
	var lastSig string

	for round := 1; round <= lim.Rounds; round++ {
		var resp *response
		for i, model := range models {
			var err error
			resp, err = c.Chat(ctx, model, msgs, reg.Specs(), maxTokens)
			if err == nil {
				// Липкая смена: удавшаяся модель становится основной до конца
				// прогона. Иначе каждый раунд платит за отказ первой.
				if i > 0 {
					rest := append([]string(nil), models...)
					rest = append(rest[:i], rest[i+1:]...)
					models = append([]string{model}, rest...)
				}
				break
			}
			// Резерв меняет модель, а не ленту: формат совместим, история та же.
			if i == len(models)-1 || !retryable(err) {
				return "", msgs, err
			}
		}

		choice := resp.Choices[0]
		spent += resp.Usage.TotalTokens
		if lim.Tokens > 0 && spent > lim.Tokens {
			return choice.Message.Content, msgs, fmt.Errorf("%w: %d токенов", ErrBudget, spent)
		}

		if choice.FinishReason != "tool_calls" || len(choice.Message.ToolCalls) == 0 {
			return choice.Message.Content, append(msgs, choice.Message), nil
		}

		// Согласованность ленты: ассистент с tool_calls, затем по одному
		// сообщению role=tool на каждый вызов, с тем же tool_call_id. Пропуск
		// одного — следующий запрос провайдер разворачивает.
		msgs = append(msgs, choice.Message)

		sig := callSignature(choice.Message.ToolCalls)
		if sig == lastSig {
			return "", msgs, ErrLoop
		}
		lastSig = sig

		for _, call := range choice.Message.ToolCalls {
			// Текст ошибки уходит модели сознательно: «нет такого инструмента»
			// и «такой записи нет» — то, по чему она перестраивается.
			result, _ := reg.Call(ctx, call)
			msgs = append(msgs, Message{Role: "tool", ToolCallID: call.ID, Content: result})
		}
	}

	return "", msgs, fmt.Errorf("%w: %d раундов", ErrBudget, lim.Rounds)
}

// callSignature — «те же вызовы, что в прошлом раунде»: аргументы повторяются
// символ в символ, и это самый дешёвый детектор цикла.
func callSignature(calls []ToolCall) string {
	h := sha256.New()
	for _, c := range calls {
		fmt.Fprintf(h, "%s|%s\n", c.Function.Name, c.Function.Arguments)
	}
	return hex.EncodeToString(h.Sum(nil))
}

// retryable — что имеет смысл менять: модель. Отказ модели или шлюза — да;
// отмена контекста и границы бюджета — нет.
func retryable(err error) bool {
	return !errors.Is(err, context.Canceled) &&
		!errors.Is(err, context.DeadlineExceeded) &&
		!errors.Is(err, ErrBudget)
}
```

## Как это тестировать без сети

```go
package agent

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"time"
)

// SelfCheck — прогон цикла против подставного провайдера: ни сети, ни ключей.
// Сценарий задаётся списком ответов, проверяются и текст, и лента, и границы.
func SelfCheck() error {
	pages := []string{
		`{"choices":[{"finish_reason":"tool_calls","message":{"role":"assistant","tool_calls":[{"id":"c1","type":"function","function":{"name":"search","arguments":"{\"q\":\"роль\"}"}}]}}],"usage":{"total_tokens":40}}`,
		`{"choices":[{"finish_reason":"stop","message":{"role":"assistant","content":"готово"}}],"usage":{"total_tokens":70}}`,
		`{"choices":[{"finish_reason":"tool_calls","message":{"role":"assistant","tool_calls":[{"id":"c2","type":"function","function":{"name":"search","arguments":"{\"q\":\"роль\"}"}}]}}],"usage":{"total_tokens":20}}`,
	}

	var served int
	var primaryReqs atomic.Int64

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var req request
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		if req.Model == "primary" {
			primaryReqs.Add(1)
			w.WriteHeader(http.StatusInternalServerError)
			fmt.Fprint(w, "перегрузка")
			return
		}

		idx := served
		if idx > len(pages)-1 {
			idx = len(pages) - 1 // последний ответ повторяется: цикл должен пойматься
		}
		served++

		w.Header().Set("content-type", "application/json")
		fmt.Fprint(w, pages[idx])
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "ключ", 5*time.Second)
	reg := NewRegistry(Tool{
		Spec: ToolSpec{Name: "search", Description: "поиск", Parameters: map[string]any{"type": "object"}},
		Fn: func(_ context.Context, args map[string]any) (string, error) {
			return "найдено: " + fmt.Sprint(args["q"]), nil
		},
	})

	ctx := context.Background()

	// Отказ основной модели → резерв, и дальше идём с резервом.
	text, msgs, err := Run(ctx, c, []string{"primary", "backup"}, reg,
		[]Message{{Role: "user", Content: "найди"}}, Limits{Rounds: 4, Tokens: 1000, Wall: 10 * time.Second}, 100)
	if err != nil {
		return fmt.Errorf("откат на резерв: %w", err)
	}
	if text != "готово" {
		return fmt.Errorf("откат на резерв: текст %q", text)
	}
	if got := primaryReqs.Load(); got != 1 {
		return fmt.Errorf("откат на резерв: основную модель дёргали %d раз(а), ожидался 1", got)
	}

	// Лента согласована: user, assistant(tool_calls), tool(result), assistant(ответ).
	if len(msgs) != 4 || msgs[2].Role != "tool" || msgs[2].ToolCallID != "c1" ||
		!strings.Contains(msgs[2].Content, "роль") {
		return fmt.Errorf("лента рассогласована: %+v", msgs)
	}

	// Повтор одного и того же вызова ловится, а не жрёт бюджет.
	if _, _, err := Run(ctx, c, []string{"backup"}, reg,
		[]Message{{Role: "user", Content: "найди"}}, Limits{Rounds: 5, Tokens: 1000}, 100); !errors.Is(err, ErrLoop) {
		return fmt.Errorf("ожидвался ErrLoop, получили %v", err)
	}

	return nil
}
```

Фейковый провайдер полезен и вне самопроверки: на нём проверяются ленточные
инварианты (каждому `tool_call` — свой `role=tool`), смена модели и границы
бюджета, и всё это остаётся юнит-тестом, который идёт доли секунды и не требует
ключа. Ответы лучше хранить как настоящие JSON-фрагменты, а не как константы
из Go: форматы аргументов и `finish_reason` меняются у провайдеров, и тест должен
ловить это на себе, а не в проде.

## Что при этом решает человек

| Вопрос | Ответ по умолчанию |
|---|---|
| Модель вызвала инструмент с необратимым эффектом | показать что и с какими аргументами и спросить; «модель так решила» — не основание |
| Инструмент вернул чужой текст (страница, письмо, выгрузка) | считать недоверенным входом: в ленту он попадает как данные, инструкции внутри него — не команды ([../../shared/security.md](../../shared/security.md)) |
| Модель просит то, чего нет в списке | ответ «такого инструмента нет» + список; в статистику это попадает как дефект промпта |
| Диалог разросся | обрезать старое, а не среднее: системный промпт и последний ответ нужны целиком, середина — кандидаты на сводку |
| Сколько стоит прогон | `usage.total_tokens` по раундам в метрику; без этого «агент стал тупее» необсуждаемо |

Аргументы инструмента проверяются по тем же правилам, что любой внешний ввод: типы, диапазоны, права вызывающего, а не «модель же не станет». Схема в описании инструмента — подсказка модели, а не валидатор.

## Related

- [structured-output.md](structured-output.md) — когда инструмент не нужен: одна операция и известная схема
- [retries-budget.md](retries-budget.md) — ретраи, кэш и деньги на уровне одного вызова
- [streaming.md](streaming.md) — стриминг текста с инструментами не дружит: аргументы по частям не разбираются
- [../rules.md](../rules.md) — правила раздела: таймауты, бюджеты, что не повторять
- [../../agenting/rules.md](../../agenting/rules.md) — тот же бюджет и право на действие на уровне агента целиком
- [../../shared/security.md](../../shared/security.md) — вывод инструмента как недоверенный вход