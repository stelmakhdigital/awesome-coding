# Go

Целевая версия: **Go 1.25** (fallback: 1.24). Закреплено на 2026-09-06.

## Состав раздела

- [rules.md](rules.md) — обязательные guardrails (✅/❌)
- [idioms.md](idioms.md) — идиоматичный Go
- [decisions.md](decisions.md) — таблицы решений: что выбрать и когда
- [snippets/](snippets/) — готовые сниппеты
- [patterns/](patterns/) — архитектурные и дизайн-паттерны

## Конвенции

- `gofmt` / `goimports` — без исключений.
- Модуль: директива `go 1.25` в `go.mod`.
- Структура проекта: `cmd/<app>` (entrypoint'ы), `internal/` (приватный код), `pkg/` (публичный API, только для библиотек).
- Имена пакетов: короткие lowercase слова, без подчёркиваний; запрещены `util`, `common`, `helpers`, `misc`.
- Ошибки: lowercase, без точки в конце, оборачивание через `%w`.
- `context.Context` — первый аргумент функции, имя `ctx`.

## Что нового в последних версиях (не пишите устаревший код)

- **1.21**: пакеты `slices`, `maps`; builtins `min`/`max`, `clear()`; loop variable — на итерацию.
- **1.22**: паттерны `http.ServeMux` (`GET /items/{id}`, `r.PathValue`); `range` по функции; `log/slog` в stdlib (с 1.21).
- **1.23**: `unique`, `math/rand/v2`, `slices.Collect`/`maps.Collect`, struct-типы в type parameters.
- **1.24**: `testing/synctest` (экспериментальный), `t.Context()`, `crypto/hkdf`, `crypto/mlkem`, `crypto/ecdh`.
- **1.25**: см. официальные release notes; в этом разделе код целевой версии 1.25.

## Инструменты

`gofmt`, `go vet`, `golangci-lint` (минимум: `errcheck`, `govet`, `staticcheck`, `unused`).
