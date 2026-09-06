# Bash

Целевая версия: **Bash 5.3** (fallback: 5.2). Закреплено на 2026-09-06.

## Состав раздела

- `README.md` — этот файл (версия, конвенции)
- [rules.md](rules.md) — guardrails (✅/❌)
- [idioms.md](idioms.md) — идиомы (массивы, mapfile, функции, строки)
- [decisions.md](decisions.md) — таблицы решений (bash vs python, инструменты)
- [snippets/](snippets/) — готовые сниппеты (error-handling, functions, files)

## Конвенции

- Шапка скрипта: `#!/usr/bin/env bash` + `set -Eeuo pipefail`.
- Имена: `snake_case` для переменных и функций; `UPPER_SNAKE` для глобальных констант.
- Кавычки: переменные **всегда** в двойных кавычках: `"$var"`, не `$var`.
- Функции: `name() { ... }`; возвращение через код (`return 1`), не через `echo`.
- Локальные переменные: `local` внутри функций.
- Сложная логика (циклы с вложенными условиями, JSON) — выносите в Python/Go, не в Bash.

## Новое в 5.3 (используйте осознанно)

- Новый формат command substitution: `${ command; }` / `${|command;}` — захват вывода **без** fork'а дочернего процесса и без пайпов.
- `trap -P` — печатает действия trap'ов по сигналам.
- `GLOBSORT` — сортировка результатов glob'а (name, size, mtime, ...; asc/desc).
- `printf %q`/`%Q` — alternate form с одинарными кавычками; `%ls`/`%lc` — wide-строки в multibyte-локали.
- Новые loadable builtins: `kv`, `strptime`.

## Инструменты

`shellcheck` (обязательно), `shfmt` (форматтер).
