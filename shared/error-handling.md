---
id: shared-error-handling
title: "Shared: Error handling (кросс-языковые принципы)"
lang: shared
min_version: null
category: concept
tags: [errors, error-handling, principles, cross-language]
status: stable
updated: 2026-09-06
---

# Error handling — принципы

**Когда использовать** — любой код, работающий с ошибками.
**Когда НЕ использовать** — n/a: базовая запись.

## Принципы

1. **Ожидаемые ошибки — не исключения**: «не найдено», «невалидный ввод», «конфликт» —
   возвращаемое значение (`null`/`Option`/`Result`/код), а не throw.
2. **Непредвиденные ошибки — пробрасывайте** (rethrow) с контекстом, не глотайте.
3. **Оборачивайте с контекстом** на границах слоёв: `failed to create order: <причина>`.
4. **Одна точка обработки**: низкие слои бросают/возвращают, высокие — решают
   (лог + ретрай + ответ пользователю).
5. **Никогда не `catch {}` / `except: pass`** без осознанного комментария.
6. **Ретрай — только для идемпотентных операций** и только на временные ошибки.

## ✅ / ❌

- ✅ `if err != nil { return fmt.Errorf("create order: %w", err) }` (Go)
- ❌ Пустой блок обработки ошибки «на всякий случай»
- ✅ Проверка ошибки сразу после вызова (не «в конце функции»)
- ❌ Логирование + возврат ошибки (двойная обработка)
- ✅ Разные типы/коды для разных причин (чтобы вызывающий мог различить)
- ❌ Одна ошибка «для всего» (`Error` с текстом «что-то пошло не так»)

## Идиомы по языкам

| Язык | Механизм | Детали |
|---|---|---|
| Go | `error` + wrap (`%w`) | [go/snippets/error-handling.md](../go/snippets/error-handling.md) |
| C# | исключения + `catch when` | [csharp/snippets/error-handling.md](../csharp/snippets/error-handling.md) |
| Kotlin | `Result` / исключения | [kotlin/snippets/coroutines.md](../kotlin/snippets/coroutines.md) |
| Python | исключения + context managers | [python/](../python/) |
| TS/JS | `throw` + typed errors | [javascript/snippets/error-handling.md](../javascript/snippets/error-handling.md) |
| C | коды возврата + `errno` | [c/snippets/error-handling.md](../c/snippets/error-handling.md) |
| Bash | `set -euo pipefail` + traps | [bash/snippets/error-handling.md](../bash/snippets/error-handling.md) |

## Пример (Go)

```go
// Цепочка wrap: контекст на каждом уровне, причина — в корне.
func CreateOrder(ctx context.Context, id string) (*Order, error) {
    order, err := loadOrder(ctx, id)
    if err != nil {
        return nil, fmt.Errorf("create order %s: %w", id, err)
    }
    if err := validateOrder(order); err != nil {
        return nil, fmt.Errorf("create order %s: %w", id, err)
    }
    return order, nil
}
```

## Related

- [testing.md](testing.md) — как тестировать ошибки
- [observability.md](observability.md) — логирование ошибок
