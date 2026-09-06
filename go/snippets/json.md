---
id: go-json
title: JSON: encoding/json и streaming
lang: go
min_version: "1.21"
category: snippet
tags: [json, encoding, stdlib]
status: stable
updated: 2026-09-06
---

# JSON

**Когда использовать** — сериализация/десериализация JSON в stdlib.
**Когда НЕ использовать** — критичная производительность: `goccy/go-json` (см. [decisions.md](../decisions.md)).

## Код

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

- `omitempty` срабатывает на zero-value: `0`, `""`, `false`, `nil`, пустой срез/мапа. Для «всегда отправлять 0» — указатель `*int`.
- `json.Marshal` по умолчанию экранирует HTML (`<` → `\u003c`); для API-ответов используйте `Encoder` + `SetEscapeHTML(false)`.
- `time.Time` сериализуется в RFC3339; кастомный формат — через `MarshalJSON`/`UnmarshalJSON`.
- Неизвестные поля молча игнорируются — для API-контрактов включайте `DisallowUnknownFields`.
- `[]byte` в структуре — base64 в JSON; если нужен массив чисел — `[]int`.

## Related

- [decisions.md — JSON](../decisions.md)
