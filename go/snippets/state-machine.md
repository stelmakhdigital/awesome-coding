---
id: go-state-machine
title: "Go: автомат состояний — таблица переходов, guard, параллельные запросы"
lang: go
min_version: "1.22"
category: snippet
tags: [state-machine, fsm, transitions, guards, idempotency, optimistic-lock, workflow, debug-mode]
status: stable
updated: 2026-11-25
---

# Автомат состояний: таблица переходов, guard, параллельные запросы

**Когда использовать** — «что разрешено после чего» является правилом продукта, а не побочным эффектом обработчиков: сессия интервью со стадиями, заявка, доставка, платёж. Переходов 4-30, они меняются редко и их надо показывать людям (схема, документ, приёмка).
**Когда НЕ использовать** — состояний два (`bool` дешевле таблицы); шаги долгие и зависят от внешних событий с ожиданием (нужна очередь и планировщик, а не автомат в памяти процесса); история важна сама по себе — тогда события как первичное хранилище ([../architecture/patterns/event-sourcing.md](../../architecture/patterns/event-sourcing.md)); переходы описываются пользователем в рантайме (тогда данные, а не код).

## Таблица переходов

```go
// Package flow — переходы по стадиям: таблица, guard, отказ на недопустимом
// событии. Разрешённая карта хранится данными, а не размазана по обработчикам.
package flow

import (
	"context"
	"errors"
	"fmt"
)

type State string
type Event string

// Стадии сессии интервью.
const (
	Idle     State = "idle"
	Question State = "question"
	Answer   State = "answer"
	Review   State = "review"
	Done     State = "done"
)

const (
	EvStart   Event = "start"
	EvSubmit  Event = "submit"
	EvReveal  Event = "reveal"
	EvSkip    Event = "skip"
	EvFinish  Event = "finish"
	EvRestart Event = "restart"
)

// ErrTransition — событие недопустимо в текущем состоянии. Это не паника и не
// 500: клиенту нужен 409 с текущим состоянием.
var ErrTransition = errors.New("переход недопустим")

// ErrConcurrent — состояние изменилось под нами.
var ErrConcurrent = errors.New("состояние изменилось параллельным запросом")

// Payload — то, что переход читает. Разные переходы берут разные поля; поля не
// связанные с переходом, в него класть не надо.
type Payload struct {
	Answer   string
	HasScore bool
}

// Rule — один переход. Guard проверяет то, чего не видно из состояний: право
// пользователя, наличие оценки, заполненность ответа. nil guard = переход
// разрешён всегда. Контекст нужен потому, что проверки почти всегда ходят наружу.
type Rule struct {
	From  State
	Event Event
	To    State
	Guard func(ctx context.Context, p Payload) error
}

// Machine — набор правил, собранный один раз. Индекс по (from,event) даёт
// O(1) проверку и ловит дубли правил на старте процесса.
type Machine struct {
	rules map[[2]string]Rule
	order []Rule
}

func New(rules ...Rule) (*Machine, error) {
	m := &Machine{rules: make(map[[2]string]Rule, len(rules)), order: rules}
	for _, r := range rules {
		key := [2]string{string(r.From), string(r.Event)}
		if _, dup := m.rules[key]; dup {
			return nil, fmt.Errorf("flow: дубль правила %s +(%s)->", r.From, r.Event)
		}
		if r.To == "" {
			return nil, fmt.Errorf("flow: у правила %s +(%s) пустая цель", r.From, r.Event)
		}
		m.rules[key] = r
	}
	return m, nil
}

// Next — целевое состояние и ошибка guard'а.
func (m *Machine) Next(ctx context.Context, cur State, ev Event, p Payload) (State, error) {
	r, ok := m.rules[[2]string{string(cur), string(ev)}]
	if !ok {
		return "", fmt.Errorf("%w: %s + %s", ErrTransition, cur, ev)
	}
	if r.Guard != nil {
		if err := r.Guard(ctx, p); err != nil {
			return "", fmt.Errorf("%w: %s + %s: %w", ErrTransition, cur, ev, err)
		}
	}
	return r.To, nil
}

// Can — проверка «разрешено ли это вообще» для UI: кнопка «Дальше» не должна
// появляться там, где сервер всё равно ответит 409.
func (m *Machine) Can(cur State, ev Event) bool {
	_, ok := m.rules[[2]string{string(cur), string(ev)}]
	return ok
}

// Validate — целостность таблицы при старте: недостижимые состояния и висячие
// переходы падают при запуске процесса, а не в тот момент, когда до стадии
// дошёл пользователь.
func (m *Machine) Validate(initial State) error {
	reached := map[State]bool{initial: true}
	changed := true
	for changed {
		changed = false
		for _, r := range m.order {
			if reached[r.From] && !reached[r.To] {
				reached[r.To] = true
				changed = true
			}
		}
	}
	for _, r := range m.order {
		if !reached[r.From] {
			return fmt.Errorf("flow: состояние %s недостижимо из %s", r.From, initial)
		}
	}
	return nil
}

// Stuck — состояния без исходящих переходов, кроме терминальных: их надо
// перечислить явно, иначе «зависшая» стадия обнаружится в проде.
func (m *Machine) Stuck(terminal ...State) []State {
	isTerminal := make(map[State]bool, len(terminal))
	for _, s := range terminal {
		isTerminal[s] = true
	}
	seen := map[State]bool{}
	var out []State
	for _, r := range m.order {
		if isTerminal[r.From] || seen[r.From] {
			continue
		}
		seen[r.From] = true
	}
	states := map[State]bool{}
	for _, r := range m.order {
		states[r.From] = true
		states[r.To] = true
	}
	for s := range states {
		if !isTerminal[s] && !seen[s] {
			out = append(out, s)
		}
	}
	return out
}
```

Таблица, из которой собирается автомат:

```go
package flow

import (
	"context"
	"fmt"
)

// Interview — карта стадий интервью. Порядок слов в комментарии читается
// вслух на созвоне с продуктом: «вопрос по submit переходит в ответ».
func Interview() (*Machine, error) {
	guardAnswer := func(_ context.Context, p Payload) error {
		if p.Answer == "" {
			return fmt.Errorf("пустой ответ")
		}
		return nil
	}
	guardScored := func(_ context.Context, p Payload) error {
		if !p.HasScore {
			return fmt.Errorf("нет оценки")
		}
		return nil
	}

	return New(
		Rule{From: Idle, Event: EvStart, To: Question},
		Rule{From: Question, Event: EvSubmit, To: Question, Guard: guardAnswer},
		Rule{From: Question, Event: EvReveal, To: Answer},
		Rule{From: Question, Event: EvSkip, To: Answer},
		Rule{From: Answer, Event: EvReveal, To: Review, Guard: guardScored},
		Rule{From: Answer, Event: EvSkip, To: Review},
		Rule{From: Review, Event: EvFinish, To: Done},
		Rule{From: Done, Event: EvRestart, To: Idle},
	)
}
```

## Переход под конкуренцией

```go
// Package flowstore — применение перехода к строке в базе: сравнил и поменял,
// а не «прочитал, подумал, записал».
package flowstore

import (
	"context"
	"errors"
	"fmt"

	"example.com/ac/flow"
)

// ErrNotFound — сессии нет (или она в другомTenant): сообщение одинаковое,
// иначе существование чужих сессий становится проверкой.
var ErrNotFound = errors.New("сессия не найдена")

// Row — то, что лежит в строке.
type Row struct {
	ID       string
	Tenant   string
	Stage    flow.State
	Answer   string
	HasScore bool
}

// Applier обновляет переходом. Реализация обязана выполнить обновление одним
// запросом с условием по текущему состоянию: два запроса («прочитать» и
// «записать») дают потерю перехода под параллельными запросами.
type Applier interface {
	Load(ctx context.Context, id, tenant string) (Row, error)
	// ApplyOne: UPDATE session SET stage=$3 WHERE id=$1 AND stage=$2.
	// Строк обновлено 0 — значит состояние уже уехало: ErrConcurrent.
	ApplyOne(ctx context.Context, id string, from, to flow.State) (bool, error)
}

type Service struct {
	m  *flow.Machine
	ap Applier
}

func NewService(m *flow.Machine, ap Applier) *Service {
	return &Service{m: m, ap: ap}
}

// Advance применяет событие к сессии.
// Повтор того же события, когда состояние уже целевое, — успех без второго
// перехода: сеть мигала, клиент повторил, ретрай на 409 создал бы алерты.
func (s *Service) Advance(ctx context.Context, id, tenant string, ev flow.Event, p flow.Payload) (flow.State, error) {
	row, err := s.ap.Load(ctx, id, tenant)
	if err != nil {
		return "", err
	}

	next, err := s.m.Next(ctx, row.Stage, ev, p)
	if errors.Is(err, flow.ErrTransition) {
		if s.m.Can(row.Stage, ev) {
			return row.Stage, err // переход есть, но guard не пустил: 422
		}
		return row.Stage, fmt.Errorf("%w (сессия в стадии %s)", err, row.Stage)
	}
	if err != nil {
		return "", err
	}

	ok, err := s.ap.ApplyOne(ctx, id, row.Stage, next)
	if err != nil {
		return "", err
	}
	if !ok {
		return row.Stage, flow.ErrConcurrent
	}
	return next, nil
}
```

Обновление с условием по старому состоянию (`WHERE stage = $2`) — тот же приём, что и оптимистичная блокировка по версии: параллельные запросы не «переезжают» друг друга, а один из них получает `ErrConcurrent` и перечитывает состояние. Молчаливый повтор перехода после конфликта — уже решение продукта, а не техники: перечитать и применить заново можно только для событий, где это безопасно.

## Дебаг-режим без дыры

Прыгнуть на стадию «разбор», не проходя всё сначала, хотят все, кто отлаживает. Разрешить это надо явно:

- Отдельное событие (`debug.jump`), которого **нет** в таблице обычных переходов: его добавляет другой автомат, собираемый под флагом. В проде флаг выключен — и перехода физически не существует, а не «запрещён guard'ом».
- Право — из авторизации, не из тела запроса: `if !user.CanDebug { return ErrTransition }` до поиска перехода.
- Переход пишется в ту же ленту событий, что и обычные, с пометкой источника: «откуда взялось это состояние» должно отвечать и через месяц.
- В тестовой среде полезнее, чем в проде: чаще «дебаг-режим» означает «мы не научились начинать с середины», и правильный ответ — тестовый фикстурный вход в нужную стадию.

## Как это тестировать

Таблица переходов уже и есть тест-матрица: по каждому правилу — «разрешён», по каждой паре (состояние × событие) вне таблицы — «отклонён с `ErrTransition`». Плюс три проверки самой таблицы: `New` не принимает дубли, `Validate` не принимает недостижимое состояние, `Stuck` не находит висячих стадий. Так правка «добавили переход» не может пройти без ответа на вопрос «а что теперь с запретом старого».

## Related

- [../react/snippets/state.md](../../react/snippets/state.md) — та же карта на клиенте: `useReducer` с таблицей переходов
- [../csharp/patterns/state-machine.md](../../csharp/patterns/state-machine.md) — реализация на C#, те же правила
- [../unity/snippets/state-machine.md](../../unity/snippets/state-machine.md) — лёгкий автомат для игровых состояний
- [../architecture/ddd/tactical/aggregate.md](../../architecture/ddd/tactical/aggregate.md) — инвариант агрегата guard'ом
- [../shared/api-design.md](../../shared/api-design.md) — 409 при недопустимом переходе, текущее состояние в ответе
- [../architecture/patterns/event-sourcing.md](../../architecture/patterns/event-sourcing.md) — когда события становятся хранилищем
