---
id: cicd-gh-cli
title: "gh в скриптах: чтение, запись, пагинация, ожидание CI"
lang: bash
min_version: "2.105"
category: snippet
tags: [gh-cli, github, api, issues, pull-request, pagination, rate-limit, jq, ci, idempotency]
status: stable
updated: 2026-11-24
---

# gh в скриптах: чтение, запись, пагинация, ожидание CI

**Когда использовать** — автоматизация вокруг репозитория из CI и локальных скриптов: поднять задачи, оставить след в issue, закрыть, выложить релиз, дождаться проверки. Авторизация — из `GH_TOKEN` в секретах, права — минимальные (для чтения задач достаточно `issues: read`).
**Когда НЕ использовать** — сложная логика с ветвлениями по десяткам полей (там API-клиент с типами честнее, чем строки `--jq` в heredoc); массовые операции по сотням репозиториев (упрётесь в лимит, а он не один и тот же у разных эндпоинтов); реакция на события (для этого webhooks, а не опрос).

## Guardrails

- Табличный вывод `gh` — для людей: его оформление меняется между версиями. В скриптах — `--json` с явным списком полей и `--jq`.
- `gh` в CI обязан быть неинтерактивным: `GH_PROMPT_DISABLED=1`, иначе запрос «введите значение» вешает job до таймаута.
- Чужой репозиторий — `--repo owner/name`, а не `cd` в клон: меньше состояний, тот же токен.
- Операция, которая может повториться (retired job, повторный запуск скрипта), обязана быть идемпотентной: сначала проверить след, потом писать.
- `gh` не имеет собственного таймаута: снаружи — `timeout` и убийство группы процессов ([../agenting/snippets/watchdog.md](../agenting/snippets/watchdog.md)).

## Чтение

```bash
# Чтение из gh в скрипте: поля явно, разбор --jq, никаких таблиц.
set -euo pipefail
export GH_PROMPT_DISABLED=1

REPO="${GH_REPO:?нужен GH_REPO вида owner/name}"

# Список задач. Два факта о `gh issue list`, на которых теряют данные:
# по умолчанию только открытые и не больше 30 штук.
open_issues() {
  gh issue list --repo "$REPO" --state open --limit 300 \
    --json number,title,labels,updatedAt \
    --jq '.[] | "\(.number)\t\(.labels | map(.name) | join(","))\t\(.title)"'
}

# Задачи по фильтру поиска. Search считает отдельно от основного лимита и
# имеет потолок на число результатов — «все задачи репо» search-ом не выгрузить.
issues_missing_release_note() {
  gh issue list --repo "$REPO" --state all --limit 200 \
    --search 'label:"needs-release-note" is:closed closed:>=2026-01-01' \
    --json number,closedAt \
    --jq '.[].number'
}

# PR на ревью: черновики отфильтрованы, иначе ревью просит у человека то, что
# ещё не готово.
prs_awaiting_review() {
  gh pr list --repo "$REPO" --state open --limit 100 \
    --json number,title,isDraft,reviewDecision \
    --jq '.[] | select(.isDraft | not) | select(.reviewDecision == "" or .reviewDecision == "REVIEW_REQUIRED") | "#\(.number) \(.title)"'
}

# Статус последней проверки коммита: одна строка, пригодная для `case`.
ci_status() {
  local ref="${1:-HEAD}"
  gh pr view --repo "$REPO" --json headRefOid,reviewDecision,statusCheckRollup \
    --jq '.statusCheckRollup | map(.conclusion // .status) | unique | join(",")' 2>/dev/null || echo "нет PR для $ref"
}

# Свободный остаток лимита: отдельный счётчик на core, search и graphql.
rate_left() {
  gh api rate_limit --jq '.resources | to_entries[] | "\(.key): \(.value.remaining)/\(.value.limit)"'
}
```

## Запись, которую можно повторить

```bash
# Запись в трекер из скрипта: след, проверка следа, Then ничего не меняем.
set -euo pipefail
export GH_PROMPT_DISABLED=1

REPO="${GH_REPO:?нужен GH_REPO вида owner/name}"
MARKER="ac-bot:audit"   # виден как текст: отчётный блок всегда в хвосте тела

# Отчёт в задаче. `gh issue comment` без флагов каждый вызов добавляет новый
# комментарий — повторный запуск job'а оставляет ленту дублей.
# --edit-last правит последний комментарий текущего пользователя,
# --create-if-none создаёт его, когда комментариев нет вовсе.
post_report() {
  local issue="$1" body="$2"
  # --edit-last правит последний комментарий текущего пользователя, даже если
  # после него писали другие. Своего ещё нет — gh откажет, и тогда обычный
  # вызов создаёт первый комментарий.
  if gh issue comment "$issue" --repo "$REPO" --body "$body" --edit-last 2>/dev/null; then
    return
  fi
  gh issue comment "$issue" --repo "$REPO" --body "$body"
}

# Если в одну задачу пишут несколько разных отчётов, «последний комментарий
# автора» уже не различает их (--edit-last — один, --delete-last --yes снимает
# последний): тогда отчёт в тело задачи. Хвост после маркера считается отчётом
# и заменяется целиком.
mark_in_body() {
  local issue="$1" text="$2" current
  current=$(gh issue view "$issue" --repo "$REPO" --json body --jq .body)
  current="${current%%"$MARKER"*}"   # старый отчёт в хвосте — отрезаем до конца
  gh issue edit "$issue" --repo "$REPO" --body "$current$MARKER $text"
}

# Метки: gh падает, если метки нет в репозитории. --force создаёт метку или
# обновляет её цвет — это идемпотентно, в отличие от «сначала посмотреть список».
ensure_label() {
  local name="$1" color="${2:-ededed}"
  gh label create "$name" --repo "$REPO" --color "$color" --force >/dev/null
}

# Закрытие с причиной: без комментария закрытие выглядит как «бот унёс задачу».
close_issue() {
  local issue="$1" reason="$2"
  gh issue close "$issue" --repo "$REPO" --comment "$reason"
}

# Релиз по тегу: --verify-tag прерывает создание, если тега нет в удалённом
# репозитории (выложили релиз из локального тега, который никуда не уехал).
# Заметки — из файла: их читают люди, и история коммитов для них не формат.
publish_release() {
  local tag="$1" notes_file="$2"
  gh release create "$tag" --repo "$REPO" --verify-tag --notes-file "$notes_file"
}
```

## Пагинация и ожидание CI

```bash
# gh api: прямой доступ к эндпоинтам, пагинация по Link, ожидание прогонов.
set -euo pipefail
export GH_PROMPT_DISABLED=1

REPO="${GH_REPO:?нужен GH_REPO вида owner/name}"

# Пагинация: --paginate проходит по Link-заголовкам. Поля перечисляем явно —
# `gh api` без --jq отдаёт весь объект, и он большой.
# Ловушка: issues включают pull request (PR — это issue с полем pull_request).
all_issue_numbers() {
  gh api --paginate "/repos/$REPO/issues?state=all&per_page=100" \
    --jq '.[] | select(.pull_request == null) | .number'
}

# Ответы вида «массив или объект» (404 у gh приходит не как пустой результат):
# ожидаемую пустоту превращаем в управляемое значение, а не в exit 1.
branch_exists() {
  local branch="$1"
  gh api "/repos/$REPO/branches/$branch" --jq .name >/dev/null 2>&1
}

# Ждём завершения прогона и отдаём его итог кодом выхода: job CI становится
# «дождись и упади, если упало». --exit-status — то, что делает ожидание
# полезным в пайплайне.
wait_ci() {
  local run_id="${1:-}"
  if [ -n "$run_id" ]; then
    gh run watch "$run_id" --repo "$REPO" --exit-status --interval 15
  else
    gh run watch --repo "$REPO" --exit-status --interval 15
  fi
}

# Логи только упавших шагов: `--log` вывалит мегабайты, `--log-failed` — то,
# за чем открывали.
failed_logs() {
  local run_id="$1"
  gh run view "$run_id" --repo "$REPO" --log-failed | tail -n 200
}

# Повторное чтение одних и тех же данных в цикле: кеш по заголовкам ответа
# экономит лимит. Не использовать, если читаем сразу после записи.
refresh_labels() {
  gh api --cache 30s "/repos/$REPO/labels" --jq '.[].name'
}
```

## Что ломается чаще всего

| Симптом | Причина | Что делать |
|---|---|---|
| Скрипт «нашёл 30 задач», их 400 | дефолт `--limit 30` и `--state open` | `--state all --limit N`; дальше — `--paginate` |
| В списке задач появились PR | `issues` включают PR | `select(.pull_request == null)` |
| Job висит 10 минут и падает по таймауту | `gh` спрашивает значение в интерактиве | `GH_PROMPT_DISABLED=1`, все значения аргументами |
| `search` вернул 1000 и молчит | потолок выдачи у search + отдельный лимит запросов | сегментировать запрос (дата, метка), не полагаться на пагинацию |
| `--paginate` не идёт дальше первой страницы | эндпоинт не отдаёт `Link` (у search — `--perPage`) | читать `.search`-ответ целиком или сегментировать |
| `gh: issue does not exist` при закрытии | задача в другом репо / нет прав у токена | `--repo` явно, права токена per-repo |
| Метка не добавляется | метки нет в репозитории | `gh label create --force` перед `--add-label` |
| Повторный запуск удвоил отчёты в задаче | `gh issue comment` каждый вызов добавляет комментарий | `--edit-last` (первый комментарий — обычным вызовом); для нескольких отчётов — блок в хвосте тела задачи |
| Пакетный прогон исчерпал лимит | чтение ради чтения в цикле | `--cache`, режесить опрос, `gh api rate_limit` как диагностика |
| Релиз выложен по тегу, которого нет в remote | `gh release create` берёт локальный тег | `--verify-tag`: без тега в удалённом репо создание прерывается |

## Related

- [../agenting/snippets/run-state.md](../agenting/snippets/run-state.md) — след в задаче для дедупликации периодического агента
- [../agenting/snippets/watchdog.md](../agenting/snippets/watchdog.md) — `gh` без собственного таймаута: внешний бюджет времени
- [../agenting/patterns/bug-hunter.md](../agenting/patterns/bug-hunter.md) — периодический агент, который пишет в трекер
- [../shared/observability.md](../shared/observability.md) — логировать что именно изменено в трекере, а не «готово»
- [rules.md](rules.md) — правила раздела: секреты, минимальные права, читаемые CI-ошибки
