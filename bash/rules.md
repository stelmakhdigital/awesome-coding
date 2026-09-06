---
id: bash-rules
title: "Bash Rules"
lang: bash
min_version: "5.3"
category: rule-set
tags: [rules, guardrails, strict-mode, safety, scripting]
status: stable
updated: 2026-09-06
---

# Bash Rules — обязательные правила

## Строгий режим

- ✅ **`set -euo pipefail`** — в начале каждого скрипта:
  - `-e`: выход при ошибке;
  - `-u`: ошибка на неопределённой переменной;
  - `-o pipefail`: ошибка пайплайна — ошибка последней команды.
- ✅ `trap cleanup EXIT` — гарантированный cleanup.
- ❌ Скрипты без `set -e` в CI/деплой-пайплайнах.

## Переменные и кавычки

- ✅ **Кавычки всегда**: `"$var"`, `"$@"`, `"${array[@]}"` — без кавычек word splitting.
- ✅ `"$@"` — аргументы скрипта (не `$*` — теряет границы).
- ✅ `${var:-default}` — дефолт; `${var:?required}` — ошибка при отсутствии.
- ✅ Имена: `UPPER_SNAKE` (глобальные), `lower_snake` (локальные, `local`).
- ❌ `eval` с внешним вводом.

## Команды

- ✅ Проверка **каждой** важной команды (`|| die "..."`), не «надеюсь».
- ✅ `command -v` для проверки наличия команды (не `which`).
- ✅ `[[ ]]` (bash) вместо `[ ]` (POSIX) — строки, regex.
- ✅ Пайплайны: `set -o pipefail` + проверка.
- ❌ `rm -rf "$dir"` без валидации `$dir` (пустая переменная = `rm -rf /`).

## Файлы

- ✅ `mktemp` для временных файлов (не `/tmp/myfile`).
- ✅ `while IFS= read -r line` — построчное чтение (не `for line in $(cat ...)`).
- ✅ Пути: `cd "$(dirname ...)"`, `realpath`.
- ✅ `find -print0` + `while IFS= read -r -d ''` — имена с пробелами/новыми строками.

## Производительность

- ✅ Субшелл `$(...)` — не backticks.
- ✅ Кэширование результатов команд в переменных (не повторный вызов).
- ✅ `mapfile`/`readarray` для массивов из вывода.
- ❌ Циклы `for` на тысячи файлов — `xargs -P` / `find -exec`.

## Related

- [idioms.md](idioms.md) — идиомы
- [decisions.md](decisions.md) — bash vs python
- [shared/security.md](../shared/security.md)
