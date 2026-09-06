---
id: bash-functions
title: "Bash: функции (ошибки, таймауты, параллелизм)"
lang: bash
min_version: "5.3"
category: snippet
tags: [functions, errors, timeout, parallel, xargs]
status: stable
updated: 2026-09-06
---

# Функции (Bash)

**Когда использовать** — переиспользуемые блоки в bash-скриптах.
**Когда НЕ использовать** — сложная логика (переносите в Python).

Код проверен на bash 5.3.0 (выполнен).

## Ошибки и логи

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# Единая точка ошибок: сообщение + контекст.
die() {
  echo "ERROR: $*" >&2
  exit 1
}

log() {
  printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" >&2
}

# Проверка зависимостей.
require() {
  local cmd
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null || die "не найдена команда: $cmd"
  done
}

require curl jq

# Таймаут для внешней команды.
run_with_timeout() {
  local secs=$1; shift
  log "запуск (таймаут ${secs}s): $*"
  timeout "$secs" "$@"
}

main() {
  local out
  out=$(run_with_timeout 5 curl -fsS https://example.com) || die "запрос не удался"
  log "получено ${#out} байт"
}

main "$@"
```

## Параллельная обработка (xargs -P)

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# Функция обрабатывает один аргумент; xargs -P — параллелизм.
process_one() {
  local file=$1
  local out
  out=$(wc -c <"$file") || return 1
  echo "$file: $out"
}
export -f process_one

# 8 параллельных потоков, по 1 файлу за вызов.
find . -name '*.log' -print0 \
  | xargs -0 -P 8 -I {} bash -c 'process_one "$@"' _ {} \
  | sort > sizes.txt

echo "обработано: $(wc -l < sizes.txt)"
```

## wait -n: ожидание одного из фоновых

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# wait -n (bash 4.3+): ждать завершение ЛЮБОГО фонового процесса.
for i in 1 2 3; do
  sleep 0.$i &
done

while (( $(jobs -rp | wc -l) > 0 )); do
  wait -n || echo "один из процессов упал"
  echo "завершился ещё один"
done
echo "все завершены"
```

## Правила

1. ✅ `die`/`log` — единый стиль; логи в stderr, данные в stdout.
2. ✅ `require` — проверка зависимостей на старте (fail fast).
3. ✅ `timeout` — на всех внешних командах.
4. ✅ `export -f` + `xargs -P` — параллелизм без GNU Parallel.
5. ✅ `wait -n` — для «N фоных, обрабатываем по мере готовности».

## Related

- [rules.md](../rules.md)
- [files.md](files.md) — файлы и блокировки
