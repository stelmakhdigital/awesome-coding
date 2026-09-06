# C — Snippets

Готовые сниппеты. Формат — [../../docs/FORMAT.md](../../docs/FORMAT.md).

| ID | Запись | Теги |
|---|---|---|
| `c-error-handling` | [error-handling.md](error-handling.md) | errors, errno, cleanup, memory |
| `c-memory` | [memory.md](memory.md) | memory, malloc, cleanup, arena, ownership |
| `c-strings` | [strings.md](strings.md) | strings, stdstring, cstr, buffer, builder |
| `c-testing` | [testing.md](testing.md) | testing, assert, harness, sanitizers |

Код проверен на Apple clang 21 (`-std=c23 -Wall -Wextra -Werror`, выполнен; ASan-чисто).
`<stdstring.h>` (C23) — против совместимой реализации (libc Darwin не имеет C23-библиотеки).
