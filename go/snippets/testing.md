---
id: go-testing
title: Testing: table-driven, subtests, benchmarks
lang: go
min_version: "1.21"
category: snippet
tags: [testing, benchmarks, subtests, stdlib]
status: stable
updated: 2026-09-06
---

# Testing

**Когда использовать** — unit-тесты, бенчмарки, fuzz-тесты.
**Когда НЕ использовать** — не применимо: это базовый слой.

## Код

```go
package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

// --- Минимальная заглушка кода под тестом ---

type Config struct{ A int }

func ParseConfig(s string) (Config, error) {
	var c Config
	if err := json.Unmarshal([]byte(s), &c); err != nil {
		return Config{}, err
	}
	return c, nil
}

// Table-driven тест.
func TestParseConfig(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    Config
		wantErr bool
	}{
		{name: "valid", input: `{"a":1}`, want: Config{A: 1}},
		{name: "empty", input: `{}`, want: Config{}},
		{name: "invalid json", input: `{`, wantErr: true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParseConfig(tt.input)
			if (err != nil) != tt.wantErr {
				t.Fatalf("ParseConfig() error = %v, wantErr %v", err, tt.wantErr)
			}
			if !tt.wantErr && !reflect.DeepEqual(got, tt.want) {
				t.Errorf("ParseConfig() = %+v, want %+v", got, tt.want)
			}
		})
	}
}

// Временные каталоги и env.
func TestWritesFile(t *testing.T) {
	t.Parallel()
	dir := t.TempDir()          // автоматически удаляется
	t.Setenv("CONFIG_DIR", dir) // несовместимо с t.Parallel()!

	path := filepath.Join(dir, "config.json")
	if err := os.WriteFile(path, []byte(`{}`), 0o600); err != nil {
		t.Fatalf("WriteFile: %v", err)
	}
	t.Cleanup(func() {
		if _, err := os.Stat(path); err != nil {
			t.Errorf("file missing after test: %v", err)
		}
	})
}

// Бенчмарк.
func BenchmarkParseConfig(b *testing.B) {
	input := `{"a":1}`
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		if _, err := ParseConfig(input); err != nil {
			b.Fatal(err)
		}
	}
}

// Fuzz-тест (1.18+).
func FuzzParseConfig(f *testing.F) {
	f.Add(`{"a":1}`)
	f.Fuzz(func(t *testing.T, input string) {
		_, _ = ParseConfig(input) // не должно паниковать
	})
}
```

## Pitfalls

- `t.Setenv` несовместим с `t.Parallel()` (panic) — не используйте вместе.
- `t.Fatal` в goroutine не остановит текущий тест — используйте `t.Errorf` + WaitGroup/канал.
- Тесты не должны зависеть от порядка и глобального состояния.
- Whitebox (`package foo`) vs blackbox (`package foo_test`): blackbox по умолчанию, whitebox — для доступа к приватному.
- `t.Parallel()` — только когда тесты изолированы.

## Related

- [rules.md — Тесты](../rules.md)
