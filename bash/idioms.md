---
id: bash-idioms
title: "Bash Idioms (5.x)"
lang: bash
min_version: "5.3"
category: idioms
tags: [idioms, style, arrays, mapfile, functions]
status: stable
updated: 2026-09-06
---

# Bash Idioms (5.x)

Код проверен на bash 5.3.0 (выполнен).

## Массивы и mapfile

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# mapfile: вывод команды в массив (без субшелл-потерь).
mapfile -t lines < <(printf 'a\nb\nc\n')
echo "${lines[0]}" "${#lines[@]}"  # a 3

# Ассоциативный массив (bash 4+).
declare -A counts
for w in apple banana apple cherry banana apple; do
  counts[$w]=$(( ${counts[$w]:-0} + 1 ))
done
echo "${counts[apple]}"  # 3

# Итерация: "${arr[@]}" — с кавычками.
for w in "${!counts[@]}"; do
  printf '%s=%s\n' "$w" "${counts[$w]}"
done | sort
```

## Функции и локальные переменные

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# Функция: локальные переменные, код возврата, не echo-возврат.
get_host() {
  local url=$1
  local host
  host=$(sed -E 's~^https?://([^/]+).*~\1~' <<<"$url")
  printf '%s' "$host"
}

# Возврат данных: stdout (чистый), логи — stderr.
main() {
  local url="https://example.com/path?q=1"
  local host
  host=$(get_host "$url")
  echo "$host"  # example.com
}
main
```

## Параметризация и аргументы

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# Разбор аргументов: getopts (краткие) или ручной цикл (долгие).
usage() { echo "usage: $0 [-v] [--out FILE] FILES..." >&2; exit 2; }

main() {
  local verbose=0
  local out="out.txt"
  local files=()
  while [[ $# -gt 0 ]]; do
    case $1 in
      -v) verbose=1; shift ;;
      --out) out=$2; shift 2 ;;
      -h|--help) usage ;;
      *) files+=("$1"); shift ;;
    esac
  done
  [[ ${#files[@]} -gt 0 ]] || usage

  echo "verbose=$verbose out=$out files=${#files[@]}"
}

# Демо: запуск с аргументами (в т.ч. с пробелами).
main -v --out custom.txt a.txt "b c.txt"
```

## Строки и преобразования

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

s="Hello, World"

# Преобразования регистра (bash 4+).
echo "${s,,}"   # hello, world
echo "${s^^}"   # HELLO, WORLD

# Замены.
echo "${s/Hello/Hi}"        # Hi, World
echo "${s//,/;}"           # Hello; World

# Обрезка.
echo "${s:0,5}"            # Hello
echo "${s: -6}"            # World

# Regex.
if [[ $s =~ ^([A-Z]+),\ (.*)$ ]]; then
  echo "first=${BASH_REMATCH[1]} rest=${BASH_REMATCH[2]}"
fi
```

## Правила

1. ✅ `mapfile` — вместо `while read` в массив (быстрее, чище).
2. ✅ Функции: `local`, чистый stdout, логи в stderr, код возврата.
3. ✅ Ручной цикл аргументов — для длинных опций (`--out`).
4. ✅ `"${s,,}"`/`"${s/...}"` — вместо `tr`/`sed` для простых преобразований.

## Related

- [rules.md](rules.md)
- [snippets/functions.md](snippets/functions.md) — продвинутые функции
