---
id: go-error-handling
title: Error handling: wrap, sentinel, errors.Is/As
lang: go
min_version: "1.20"
category: snippet
tags: [errors, error-handling, stdlib]
status: stable
updated: 2026-09-06
---

# Error handling

**Когда использовать** — любой код, который возвращает ошибки.
**Когда НЕ использовать** — не применимо: это базовый слой.

## Код

```go
package storage

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"os"
)

// --- Минимальные доменные типы (заглушки для самодостаточности) ---

type Config struct {
	A int `json:"a"`
}

type Item struct {
	ID   string
	Name string
}

type repo struct{}

func (repo) Find(id string) (Item, error) {
	return Item{}, ErrNotFound
}

type Store struct {
	repo repo
}

// Sentinel-ошибки — для ожидаемых условий.
var (
	ErrNotFound      = errors.New("not found")
	ErrAlreadyExists = errors.New("already exists")
)

// Пользовательский тип ошибки с полями.
type ValidationError struct {
	Field  string
	Reason string
}

func (e *ValidationError) Error() string {
	return fmt.Sprintf("invalid %s: %s", e.Field, e.Reason)
}

// Оборачивание с контекстом на каждом уровне.
func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read config %s: %w", path, err)
	}
	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parse config %s: %w", path, err)
	}
	return &cfg, nil
}

// Проверка: sentinel через errors.Is.
func (s *Store) Get(id string) (Item, error) {
	it, err := s.repo.Find(id)
	if errors.Is(err, ErrNotFound) {
		return Item{}, fmt.Errorf("get item %s: %w", id, err)
	}
	if err != nil {
		return Item{}, fmt.Errorf("get item %s: %w", id, err)
	}
	return it, nil
}

// Извлечение конкретного типа: errors.As.
func HandleValidationError(err error) {
	var vErr *ValidationError
	if errors.As(err, &vErr) {
		log.Printf("validation: field %s: %s", vErr.Field, vErr.Reason)
	}
}
```

## Pitfalls

- Не теряйте цепочку: `%w`, а не `%v`, когда нужны `Is`/`As`.
- Не оборачивайте одну и ту же ошибку несколько уровней с одинаковым текстом.
- `errors.Is` работает по всей цепочке; `==` — только для sentinel'ов своего пакета.
- Не создавайте новые ошибки в каждом уровне, если контекст уже добавлен выше.

## Related

- [rules.md — Ошибки](../rules.md)
- [logging.md](logging.md)
