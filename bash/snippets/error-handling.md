---
id: bash-error-handling
title: "Error handling: strict mode, ERR/EXIT traps"
lang: bash
min_version: "5.2"
category: snippet
tags: [errors, traps, strict-mode, cleanup]
status: stable
updated: 2026-09-06
---

# Error handling

**Когда использовать** — любой production-скрипт Bash.
**Когда НЕ использовать** — интерактивные one-liner'ы в терминале.

## Код

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# ERR trap: номер строки ошибки (BASH_LINENO[0] — строка, где была ошибка).
on_error() {
  local exit_code=$? line_no=${1:-?}
  printf 'ERROR: line %s, exit code %s\n' "$line_no" "$exit_code" >&2
}
trap 'on_error "${BASH_LINENO[0]}"' ERR

# EXIT trap: cleanup при любом выходе.
tmpdir=""
cleanup() {
  if [[ -n "$tmpdir" ]]; then
    rm -rf "$tmpdir"
  fi
}
trap cleanup EXIT

# Функции: код возврата, а не echo.
run() {
  printf 'running: %s\n' "$*"
  "$@"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'missing command: %s\n' "$1" >&2
    return 1
  fi
}

main() {
  require_cmd curl
  require_cmd jq

  tmpdir="$(mktemp -d)"
  run mkdir -p "$tmpdir/sub"

  # Внешние команды: проверяйте явно, если результат важен.
  local data
  data="$(curl -fsS https://api.example.com/items)" || return 1
  printf '%s\n' "$data" | jq -r '.[]'
}

main "$@"
```

## Pitfalls

- `set -e` **не срабатывает** в контекстах `if`, `||`, `&&`, `while` — проверяйте критичные команды явно.
- `set -u` + необязательные переменные: `${var:-default}`.
- `pipefail` — без него ошибка в середине пайплайна теряется.
- Всегда кавычки: `"$var"`; без них — word splitting и globbing.
- `local var="$(cmd)"` скрывает код возврата `cmd` — разделяйте: `local var; var="$(cmd)"`.
- `trap ... ERR` требует `set -E` (inherit_errexit), чтобы срабатывать в функциях.

## Related

- [shared/error-handling.md](../../shared/error-handling.md) — кросс-языковые принципы
