---
id: bash-files
title: "Bash: файлы (безопасность, блокировки, temp)"
lang: bash
min_version: "5.3"
category: snippet
tags: [files, temp, flock, safety, paths]
status: stable
updated: 2026-09-06
---

# Файлы (Bash)

**Когда использовать** — работа с файлами в bash-скриптах.
**Когда НЕ использовать** — сложная обработка (Python).

Код проверен на bash 5.3.0 (выполнен).

## Безопасные операции

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# rm: никогда с пустой переменной.
safe_rm() {
  local dir=$1
  [[ -n $dir && $dir != "/" ]] || { echo "отказ: пустой/корневой путь" >&2; return 1; }
  [[ $dir == /* ]] || { echo "отказ: только абсолютные пути" >&2; return 1; }
  rm -rf -- "$dir"
}

# mkdir -p с проверкой.
ensure_dir() {
  local dir=$1
  [[ -n $dir ]] || return 1
  mkdir -p -- "$dir"
}

# Чтение построчно: IFS= read -r (без обрезки пробелов и интерпретации \).
count_lines() {
  local file=$1 n=0 line
  while IFS= read -r line || [[ -n $line ]]; do
    (( ++n ))
  done <"$file"
  echo "$n"
}

# find с безопасными именами (пробелы, новые строки).
find_safe() {
  local pattern=$1
  local f
  while IFS= read -r -d '' f; do
    echo "$f"
  done < <(find . -name "$pattern" -print0)
}
```

## Временные файлы и cleanup

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# mktemp + trap: гарантированный cleanup.
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

work_file="$tmpdir/work.txt"
echo "data" >"$work_file"
echo "размер: $(wc -c <"$work_file")"
# tmpdir удалится при выходе (любом).
```

## Блокировки (flock)

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# flock: взаимное исключение между процессами.
# flock — утилита Linux (util-linux); на macOS её нет — проверяем наличие.
LOCK_FILE="/tmp/my-script.lock"

if ! command -v flock >/dev/null; then
  echo "flock не найден — блокировка отключена (установите util-linux)" >&2
else
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    echo "скрипт уже запущен (lock: $LOCK_FILE)" >&2
    exit 1
  fi
fi

# Критическая секция (lock держится до закрытия fd 9 / выхода).
echo "критическая секция, pid=$$"
sleep 0.1
echo "готово"
# fd 9 закроется при выходе — lock освободится.
```

## Правила

1. ✅ **`safe_rm`**: валидация пути до `rm -rf` (пустая переменная = катастрофа).
2. ✅ `mktemp -d` + `trap ... EXIT` — временные файлы.
3. ✅ `flock` — для «один экземпляр» (демоны, cron-скрипты).
4. ✅ `find -print0` + `read -d ''` — имена с пробелами.
5. ❌ `for f in *` для файлов (глоб не переживёт имена с пробелами).

## Related

- [rules.md](../rules.md)
- [functions.md](functions.md) — ошибки и таймауты
