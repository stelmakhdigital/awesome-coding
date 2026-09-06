---
id: go-functional-options
title: Functional Options
lang: go
min_version: "1.21"
category: pattern
tags: [design, configuration, api, options]
status: stable
updated: 2026-09-06
---

# Functional Options

**Проблема** — конструктор с множеством опциональных параметров: перегрузки не работают, struct-конфиг с кучей полей — громоздк.
**Решение** — variadic-функции-модификаторы: каждый опциональный параметр — функция `Option`, применяемая к объекту.
**Когда использовать** — 3+ опциональных параметра с разумными дефолтами.
**Когда НЕ использовать** — 1–2 параметра: передавайте явно; не создавайте Option на каждое поле.

## Код

```go
package server

import (
	"errors"
	"log/slog"
	"time"
)

type Server struct {
	addr    string
	timeout time.Duration
	logger  *slog.Logger
}

type Option func(*Server)

func WithAddr(addr string) Option {
	return func(s *Server) { s.addr = addr }
}

func WithTimeout(d time.Duration) Option {
	return func(s *Server) { s.timeout = d }
}

func WithLogger(l *slog.Logger) Option {
	return func(s *Server) { s.logger = l }
}

func New(opts ...Option) (*Server, error) {
	s := &Server{
		addr:    ":8080",
		timeout: 30 * time.Second,
		logger:  slog.Default(),
	}
	for _, opt := range opts {
		opt(s)
	}
	if err := s.validate(); err != nil {
		return nil, err
	}
	return s, nil
}

func (s *Server) validate() error {
	if s.timeout <= 0 {
		return errors.New("timeout must be positive")
	}
	return nil
}

// Использование (внутри пакета server).
func exampleUsage() {
	srv, err := New(
		WithAddr(":9090"),
		WithTimeout(10*time.Second),
	)
	if err != nil {
		return
	}
	_ = srv
}
```

## Trade-offs

- **Плюсы**: читаемый API, дефолты в одном месте, легкое тестирование, backward-compatible расширение.
- **Минусы**: опции не типизированы по объекту (любой Option можно применить к любому), «магия» closures.
- **Альтернативы**: struct-конфиг (`New(cfg Config)`) — когда опций много и они группированы; явные параметры — когда их мало.
- Валидация — в `New`, не в опциях.

## Related

- [idioms.md — Variadic + функциональные опции](../idioms.md)
