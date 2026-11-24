---
id: agenting-watchdog
title: "bash: лимит времени и убийство группы процессов у прогона"
lang: agenting
min_version: "5.3"
category: snippet
tags: [bash, timeout, setsid, process-group, watchdog, budget, output-limit, self-test]
status: stable
updated: 2026-11-25
---

# Лимит времени и убийство группы процессов

**Когда использовать** — прогон запускает то, что может висеть: вызов модели, `npm install`, сборка, CLI агента. Виснуть может не сам процесс, а его ребёнок, и тогда «убить агента» проблему не решает.
**Когда НЕ использовать** — процесс под контролем systemd (`TimeoutStopSec` + `KillMode=control-group` делают то же надёжнее) или под Kubernetes с `activeDeadlineSeconds`. Там группа процессов — забота надзирателя, а не скрипта.

## Скрипт

```bash
#!/usr/bin/env bash
# shellcheck shell=bash
# run-capped.sh — запуск с бюджетом времени и потолком вывода.

set -euo pipefail

TIME_BUDGET="${TIME_BUDGET:-300}"   # секунды на всю команду
KILL_AFTER="${KILL_AFTER:-10}"      # сколько живёт TERM до KILL
MAX_LINES="${MAX_LINES:-2000}"      # строк, которые отдаём наружу
LOG_DIR="${LOG_DIR:-/var/tmp/ac-run/log}"

# run_capped <лог> <команда...>
# Код возврата: как у команды; 143 — убиты TERM по бюджету, 137 — KILL.
run_capped() {
  local log="$1"; shift
  mkdir -p "$(dirname "$log")"

  # Отдельная сессия = отдельная группа процессов: всё, что народит команда,
  # достаётся одним выстрелом. Убийство только прямого ребёнка оставляет висеть
  # ровно то, что обычно и висит — дочерний процесс с открытым соединением.
  setsid "$@" >"$log" 2>&1 &
  local pid=$! st=0

  # Таймер — тоже в своей группе, чтобы его можно было снять вместе с его sleep
  # и не оставить сироту, который через минуту убьёт чужую уже группу.
  # bash, а не sh: встроенный kill в dash (это /bin/sh в Debian и Alpine) не
  # понимает «-- -PID», и тогда группа не убивается, а таймер молчит.
  setsid bash -c '
    sleep "$1"
    kill -TERM -- "-$2" 2>/dev/null || true
    sleep "$3"
    kill -KILL -- "-$2" 2>/dev/null || true
  ' _ "$TIME_BUDGET" "$pid" "$KILL_AFTER" &
  local timer=$!

  wait "$pid" || st=$?
  kill -- "-$timer" 2>/dev/null || true
  wait "$timer" 2>/dev/null || true
  return "$st"
}

# emit <лог> — наружу не больше MAX_LINES: лог агента на 200 КБ в теле issue не читают, а трекер режет сообщение.
emit() {
  local log="$1" lines
  lines="$(wc -l <"$log")"
  if (( lines > MAX_LINES )); then
    head -n "$MAX_LINES" "$log"
    printf '… обрезано: всего %s строк, полный лог: %s\n' "$lines" "$log"
  else
    cat "$log"
  fi
}

if [[ "${1:-}" == "--self-test" ]]; then
  tmp="$(mktemp -d)"
  # shellcheck disable=SC2064  # tmp подставляется сейчас, а не в ловушке
  trap "rm -rf '$tmp'" EXIT

  # 1. Быстрая команда отрабатывает штатно.
  TIME_BUDGET=10 run_capped "$tmp/fast.log" sh -c 'echo готово'
  grep -q готово "$tmp/fast.log" || { echo "FAIL: вывод не записан"; exit 1; }

  # 2. Висячая команда убивается в бюджете вместе с потомком.
  start="$(date +%s)"
  CHILD_PID_FILE="$tmp/child" TIME_BUDGET=2 KILL_AFTER=1 \
    run_capped "$tmp/slow.log" bash -c 'sleep 60 & echo $! >"$CHILD_PID_FILE"; wait' && st=0 || st=$?
  elapsed=$(( $(date +%s) - start ))

  (( st != 0 )) || { echo "FAIL: висячая команда завершилась успешно"; exit 1; }
  (( elapsed <= 6 )) || { echo "FAIL: убивали $elapsed с"; exit 1; }
  if [[ -s "$tmp/child" ]] && kill -0 "$(cat "$tmp/child")" 2>/dev/null; then
    echo "FAIL: потомок пережил убийство группы"; exit 1
  fi

  # 3. Лог полный, наружу — ограниченное число строк.
  run_capped "$tmp/noisy.log" bash -c 'seq 1 5000'
  logged="$(wc -l <"$tmp/noisy.log")"
  (( logged == 5000 )) || { echo "FAIL: в логе $logged строк"; exit 1; }
  printed="$(MAX_LINES=50 emit "$tmp/noisy.log" | wc -l)"
  (( printed <= 51 )) || { echo "FAIL: напечатано $printed строк"; exit 1; }

  echo "ok: бюджет, убийство группы и потолок вывода работают"
  exit 0
fi

# Основной путь — только когда файл запустили как скрипт. Тогда же его можно
# и источниковать, получив run_capped/emit без побочных эффектов.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  mkdir -p "$LOG_DIR"
  log="$LOG_DIR/$(date +%Y%m%dT%H%M%S).log"
  if run_capped "$log" "$@"; then
    emit "$log"
  else
    st=$?
    emit "$log" >&2
    exit "$st"
  fi
fi
```

Прогон самопроверки:

```console
$ TIME_BUDGET=2 bash run-capped.sh --self-test
ok: бюджет, убийство группы и потолок вывода работают
```

## Почему не `timeout`

| Способ | Что убивает | Проблема |
|---|---|---|
| `timeout 60 cmd` | только `cmd` | дети `cmd` остаются висять с открытыми сокетами и держат замок |
| `timeout -k 5 60 cmd` | то же, дважды | та же проблема с детьми |
| `setsid` + `timeout` | `cmd` в новой сессии | `timeout` шлёт сигнал по pid, а не по группе — дети живы |
| `sh -c 'kill -TERM -- -$pid'` | ничего | `kill` в dash (`/bin/sh` в Debian/Alpine) не разбирает `-- -PID`: таймер работает молча |
| Скрипт выше | группа целиком | свой механизм, его надо тестировать (self-test внутри) |

Под systemd этот же результат даёт `KillMode=control-group` (по умолчанию и есть) плюс `TimeoutStopSec`; писать своё имеет смысл там, где systemd недоступен — в контейнере прогона, на раннере CI, в cron на чужой машине.

## Как это встраивается в прогон

```bash
#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=/dev/null
. ./run-capped.sh

if run_capped "$LOG_DIR/run.log" agent-cli --task "проверить диф" </dev/null; then
  emit "$LOG_DIR/run.log" | tail -n 200 | send_report      # отчёт — в трекер
else
  st=$?
  case "$st" in
    124 | 137 | 143) notify "прогон не влез в бюджет ($st)"; exit 2 ;;
    *) notify "прогон упал с $st"; exit 1 ;;
  esac
fi
```

`</dev/null` обязателен у интерактивного CLI в прогоне: агент, которому не хватает stdin, ждёт ввода и висит ровно до бюджета. Коды 124/137/143 — отдельная ветка отчёта: «не успел» и «сломался» требуют разных действий, и это видно по коду, а не по концу лога.

## Related

- [lockfile.md](lockfile.md) — замок держится этим процессом: живое висячее дерево держит и замок
- [run-state.md](run-state.md) — чекпоинт: что уже обработано до того, как прогон убили
- [rules.md](../rules.md) — «жёсткий лимит времени» и «стоп-условие»
- [../../go/snippets/proxy.md](../../go/snippets/proxy.md) — те же границы на стороне HTTP
- [../../bash/error-handling.md](../../bash/snippets/error-handling.md) — коды возврата и ловушки в bash
