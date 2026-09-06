---
id: go-json
title: JSON: encoding/json/v2 (1.27+) и v1
lang: go
min_version: "1.21"
category: snippet
tags: [json, encoding, stdlib, v2]
status: stable
updated: 2026-09-06
---

# JSON

**Когда использовать** — сериализация/десериализация JSON: `encoding/json/v2` (Go 1.27+, рекомендуется), `encoding/json` (v1) — для Go < 1.27.
**Когда НЕ использовать** — критичная производительность: `goccy/go-json` (см. [decisions.md](../decisions.md)).

## Код

### encoding/json/v2 (Go 1.27+, рекомендуется)

```go
package api

import (
	"encoding/json/v2"
	"io"
)

type Item struct {
	ID   string   `json:"id"`
	Name string   `json:"name,omitempty"`
	Tags []string `json:"tags"`
}

// Marshal / Unmarshal — API, совместимый с v1, плюс variadic Options.
func (i Item) MarshalJSON() ([]byte, error) {
	return json.Marshal(i)
}

func UnmarshalItem(data []byte) (Item, error) {
	var i Item
	if err := json.Unmarshal(data, &i); err != nil {
		return Item{}, err
	}
	return i, nil
}

// Стриминг: MarshalWrite — в io.Writer, UnmarshalRead — из io.Reader.
func WriteItem(w io.Writer, i Item) error {
	return json.MarshalWrite(w, i)
}

func ReadItem(r io.Reader) (Item, error) {
	var i Item
	if err := json.UnmarshalRead(r, &i); err != nil {
		return Item{}, err
	}
	return i, nil
}
```

Низкоуровневая синтаксическая обработка (токены/значения) — `encoding/json/jsontext`.

### encoding/json (v1, Go < 1.27)

```go
package api

import (
	"bytes"
	"encoding/json"
	"io"
)

type Item struct {
	ID   string   `json:"id"`
	Name string   `json:"name,omitempty"`
	Data []byte   `json:"data,omitempty"` // автоматически base64
	Tags []string `json:"tags"`
}

// Marshal / Unmarshal.
func (i Item) Marshal() ([]byte, error) {
	return json.Marshal(i)
}

func UnmarshalItem(data []byte) (Item, error) {
	var i Item
	if err := json.Unmarshal(data, &i); err != nil {
		return Item{}, err
	}
	return i, nil
}

// Streaming: Encoder/Decoder — быстрее, меньше аллокаций.
func WriteItem(w io.Writer, i Item) error {
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false) // не экранировать <, >, &
	return enc.Encode(i)
}

func ReadItem(r io.Reader) (Item, error) {
	var i Item
	dec := json.NewDecoder(r)
	dec.DisallowUnknownFields() // строгий парсинг
	if err := dec.Decode(&i); err != nil {
		return Item{}, err
	}
	return i, nil
}

// Строгий парсинг из буфера.
func StrictUnmarshal(data []byte, v any) error {
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.DisallowUnknownFields()
	return dec.Decode(v)
}
```

## Pitfalls

### v2 (1.27+)

- Строгие дефолты: отклоняются невалидный UTF-8 в строках и дублирующиеся имена в объекте.
- Полный список поведенческих отличий от v1 и доступных Options — в документации пакета.
- v1 с 1.27 работает на v2-реализации: поведение сохранено, но точный текст ошибок может отличаться.

### v1

- `omitempty` срабатывает на zero-value: `0`, `""`, `false`, `nil`, пустой срез/мапа. Для «всегда отправлять 0» — указатель `*int`.
- `json.Marshal` по умолчанию экранирует HTML (`<` → `\u003c`); для API-ответов используйте `Encoder` + `SetEscapeHTML(false)`.
- `time.Time` сериализуется в RFC3339; кастомный формат — через `MarshalJSON`/`UnmarshalJSON`.
- Неизвестные поля молча игнорируются — для API-контрактов включайте `DisallowUnknownFields`.
- `[]byte` в структуре — base64 в JSON; если нужен массив чисел — `[]int`.

## Related

- [decisions.md — JSON](../decisions.md)
