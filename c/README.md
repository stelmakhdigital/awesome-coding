# C

Целевой стандарт: **C23 (ISO/IEC 9899:2024)** (fallback: C17). Закреплено на 2026-09-06.

## Состав раздела

- `README.md` — этот файл (версия, конвенции)
- [rules.md](rules.md) — guardrails (✅/❌)
- [idioms.md](idioms.md) — идиомы (init/cleanup, C23: auto/typeof/nullptr)
- [decisions.md](decisions.md) — таблицы решений (язык, аллокатор, строки, тесты)
- [snippets/](snippets/) — готовые сниппеты (error-handling, memory, strings, testing)

## Конвенции

- Компиляция: `clang -std=c23 -Wall -Wextra -Werror -Wpedantic` (GCC: `-std=c23`).
- Sanitizers в dev/CI: `-fsanitize=address,undefined`.
- Имена: `snake_case`; функции-геттеры/сеттеры — `obj_get_field`/`obj_set_field`.
- Ошибки: коды возврата + `errno` для системных вызовов; cleanup — через `goto` (идиома).
- `[[nodiscard]]` (C23) — на функциях, чей результат нельзя игнорировать.
- `bool` — из `<stdbool.h>`; `NULL` — из `<stddef.h>`.

## Новое в C23 (используйте, а не C17-обходные пути)

- Атрибуты: `[[nodiscard]]`, `[[maybe_unused]]`, `[[deprecated]]`, `[[likely]]`, `[[unlikely]]`.
- `#embed` — встраивание файлов в строки/байты.
- `<stdckdint.h>` — checked-арифметика (`ckd_add` и т.д.).
- `<stdalign.h>`, `<stdatomic.h>`, `<stdnoreturn.h>` — в stdlib (были draft'ом в C11).
- Улучшенная поддержка `bool` и логических операторов.

## Инструменты

`clang`/`gcc`, `clang-tidy`, `cmake` (или `meson`), sanitizers, `valgrind`.
