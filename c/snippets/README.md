# C — Snippets

Готовые сниппеты. Формат — [../../docs/FORMAT.md](../../docs/FORMAT.md).

| ID | Запись | Теги |
|---|---|---|
| `c-error-handling` | [error-handling.md](error-handling.md) | errors, errno, cleanup, memory |
| `c-memory` | [memory.md](memory.md) | memory, malloc, cleanup, arena, ownership |
| `c-strings` | [strings.md](strings.md) | strings, buffer, snprintf, memcpy, builder |
| `c-testing` | [testing.md](testing.md) | testing, assert, harness, sanitizers |

Код раздела проверен `make verify` (gcc 14.3, `-std=c23 -Wall -Wextra`); записи с
`verified: executed` дополнительно скомпилированы с `-Werror` и выполнены в контейнере.
Безопасной строковой библиотеки в C23 нет — см. [strings.md](strings.md).
