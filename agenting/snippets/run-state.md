---
id: agenting-run-state
title: "bash: чекпоинт прогона и дедупликация вывода в трекере"
lang: agenting
min_version: "5.3"
category: snippet
tags: [bash, checkpoint, state, idempotency, gh, github, dedup, marker, tracker, self-test]
status: stable
updated: 2026-11-25
---

# Чекпоинт прогона и дедупликация вывода

**Когда использовать** — прогон обрабатывает поток входа (коммиты, строки отчёта, очередь задач) и должен уметь: не делать дважды, узнать «докуда дошли» после убийства по бюджету и не заводить десятый issue о том же самом.
**Когда НЕ использовать** — одноразовые прогоны без повторяющегося входа; состояние на несколько машин и планировщиков (нужен внешний хранитель — [../../database/snippets/redis.md](../../database/snippets/redis.md), строка в БД с условием `WHERE version = …`).

## Чекпоинт

```bash
#!/usr/bin/env bash
# shellcheck shell=bash
# state.sh — «докуда дошли» между прогонами.

set -euo pipefail

STATE_FILE="${STATE_FILE:-.agent-state/scan.env}"

# state_get <ключ> — значение или пустая строка, если состояния ещё нет.
state_get() {
  local key="$1" line=""
  if [[ -f "$STATE_FILE" ]]; then
    line="$(grep -m1 "^${key}=" "$STATE_FILE" || true)"
  fi
  printf '%s' "${line#"${key}="}"
}

# state_set <ключ> <значение> — запись целиком файла атомарно: прогон, убитый
# посреди записи, не оставляет полфайла, в котором ключ потерян.
state_set() {
  local key="$1" value="$2" tmp
  mkdir -p "$(dirname "$STATE_FILE")"
  tmp="$(mktemp "${STATE_FILE}.XXXXXX")"
  if [[ -f "$STATE_FILE" ]]; then
    grep -v "^${key}=" "$STATE_FILE" >"$tmp" || true
  fi
  printf '%s=%s\n' "$key" "$value" >>"$tmp"
  mv -f "$tmp" "$STATE_FILE"
}

# unchanged <вход> — 0, если этот вход уже обработан (прогон выходит молча).
unchanged() {
  local current="$1"
  [[ -n "$current" ]] && [[ "$current" == "$(state_get last_input)" ]]
}

if [[ "${1:-}" == "--self-test" ]]; then
  tmp="$(mktemp -d)"
  # shellcheck disable=SC2064  # tmp подставляется сейчас, а не в ловушке
  trap "rm -rf '$tmp'" EXIT

  STATE_FILE="$tmp/state.env" state_set last_input deadbeef
  got="$(STATE_FILE="$tmp/state.env" state_get last_input)"
  [[ "$got" == "deadbeef" ]] || { echo "FAIL: прочитали '$got'"; exit 1; }

  # Тот же вход — выход молча; новый — работа.
  STATE_FILE="$tmp/state.env" unchanged deadbeef || { echo "FAIL: повтор не распознан"; exit 1; }
  if STATE_FILE="$tmp/state.env" unchanged cafebabe; then
    echo "FAIL: новый вход сочтён повтором"; exit 1
  fi

  # Два ключа в одном файле не затирают друг друга.
  STATE_FILE="$tmp/state.env" state_set last_run "2026-11-25"
  [[ "$(STATE_FILE="$tmp/state.env" state_get last_run)" == "2026-11-25" ]] || { echo "FAIL: второй ключ потерян"; exit 1; }
  [[ "$(STATE_FILE="$tmp/state.env" state_get last_input)" == "deadbeef" ]] || { echo "FAIL: первый ключ потерян"; exit 1; }

  # После записи нет временных хвостов.
  left=$(find "$tmp" -name 'state.env.*' | wc -l)
  (( left == 0 )) || { echo "FAIL: осталось $left временных файлов"; exit 1; }

  echo "ok: чекпоинт читается, повторяющийся вход узнаётся"
  exit 0
fi
```

Состояние — обычный `KEY=value`, а не JSON: `grep` разбирает его без зависимостей, а дифф в репозитории остаётся читаемым. Ключевое поле — `last_input` (sha коммита, id строки отчёта, номер страницы очереди), и обновлять его надо **после** того, как результат записан, а не до: иначе убитый по бюджету прогон оставит «обработано» на том, что не обработал.

## Дедупликация вывода

```bash
#!/usr/bin/env bash
# shellcheck shell=bash
# report.sh — один дефект — одна задача: обновить существующую вместо новой.

set -euo pipefail

LABEL="${LABEL:-agent-scan}"
REPO="${REPO:-}"                      # пусто = репозиторий из текущего каталога
MARK_KEY="${MARK_KEY:-ac-scan}"       # метка в теле issue: по ней ищем «то же самое»

# repo_args — ключ --repo, когда прогон запускают вне рабочего каталога git.
repo_args() { if [[ -n "$REPO" ]]; then printf '%s\n' --repo "$REPO"; fi; }

# find_issue <ключ> — номер открытой задачи с такой меткой в теле, пусто если нет.
find_issue() {
  local key="$1"
  local body_re="<!-- ${MARK_KEY}: ${key} -->"
  local repo=()
  mapfile -t repo < <(repo_args)

  # Поиск по метке, а не по тексту: формулировка агента меняется от прогона
  # к прогону, метка — нет.
  # shellcheck disable=SC2016  # $re — переменная jq, её раскрывать не надо
  gh issue list "${repo[@]}" --label "$LABEL" --state open --limit 200 \
    --json number,body --jq --arg re "$body_re" \
    '.[] | select(.body | contains($re)) | .number' | head -n 1
}

# report <ключ> <заголовок> <файл-тела> — создаёт или дополняет задачу.
# Возвращает 0, даже когда задача уже была: «ничего нового» — не ошибка.
report() {
  local key="$1" title="$2" bodyfile="$3"
  local repo=()
  mapfile -t repo < <(repo_args)

  # Метка внутри тела — то, по чему следующий прогон найдёт эту задачу.
  if ! grep -q "<!-- ${MARK_KEY}: ${key} -->" "$bodyfile"; then
    printf '\n<!-- %s: %s -->\n' "$MARK_KEY" "$key" >>"$bodyfile"
  fi

  local existing
  existing="$(find_issue "$key" || true)"

  if [[ -n "$existing" ]]; then
    gh issue comment "$existing" "${repo[@]}" --body-file "$bodyfile"
    printf 'дополнена задача #%s\n' "$existing"
    return 0
  fi

  local number
  number="$(gh issue create "${repo[@]}" --label "$LABEL" --title "$title" --body-file "$bodyfile")"
  printf 'создана задача: %s\n' "$number"
}
```

gh-часть в самопроверку не входит: она требует сети и токена. Проверяется тем же прогоном, что и остальной bash (`shellcheck`), плюс один ручной прогон на тестовом репозитории — прежде чем автоматизация начнёт плодить задачи в настоящем.

## Что ломается первым

| Ситуация | Решение |
|---|---|
| Sha, записанная в чекпоинте, исчезла (rebase, force-push, squash) | не падать: состояние = «ветвь + время последнего прогона», а дифф брать через `git log --since` |
| Прогон убит на середине входа | `last_input` обновляется после записи результата, поэтому следующий начнёт с того же места; дедуп по метке не даст задвоить вывод |
| Метка `agent-scan` не заведена | `gh label create agent-scan --force --color 5319e7 --description "найдено автоматизацией"` (`--force` вместо «создать, если нет»: отдельного флага нет) |
| Тело issue длиннее лимита сайта | в тело — вывод и доказательство, полный лог ссылкой на артефакт; обрезать по верхним N строк ([watchdog.md](watchdog.md)) |
| Задача закрыта, дефект вернулся | `gh issue reopen` с комментарием вместо новой задачи: история — часть ценности трекера |
| Токен без права записи | `gh` вернёт 403; это не переходящая ошибка — прогон обязан выйти с 1 и сказать про скоуп, а не ретраить |

## Related

- [lockfile.md](lockfile.md) — чекпоинт пишется под замком, иначе два прогона пишут наперегонки
- [watchdog.md](watchdog.md) — убийство по бюджету: почему порядок «сначала результат, потом чекпоинт»
- [../patterns/bug-hunter.md](../patterns/bug-hunter.md) — автоматизация, где эти два механизма работают вместе
- [../../cicd/github-actions.md](../../cicd/github-actions.md) — `GITHUB_TOKEN`, `permissions`, кэш
- [../../shared/commits.md](../../shared/commits.md) — как подписывать коммиты прогона
