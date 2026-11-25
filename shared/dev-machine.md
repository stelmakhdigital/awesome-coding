---
id: shared-dev-machine
title: "Машина под агента: неинтерактивный git, ключи, worktree, проверка тулчейна"
lang: bash
min_version: null
category: concept
tags: [dev-machine, git, ssh, worktree, credentials, non-interactive, toolchain, doctor, cleanup]
status: stable
updated: 2026-11-24
proof: "doctor, wt_add/wt_rm, maintenance и clean_tree прогнаны в bash 5.3 + git 2026-11-24: upstream у новой ветки не main, .env переживает clean"
---

# Машина под агента: неинтерактивный git, ключи, worktree, проверка тулчейна

**Когда использовать** — код на машине пишет не человек: агент, сборщик, периодический job. Отличия от человеческой машины не в пакете установленных утилит, а в том, что интерактивный вопрос означает зависшее задание, а чужой leftover в рабочем дереве означает испорченную задачу.
**Когда НЕ использовать** — личная разработка, где интерактив это и есть рабочий процесс; боевой раннер CI, где окружение описано в workflow и живёт один job ([../cicd/github-actions.md](../cicd/github-actions.md)); машина с доступом к прод-данным (там настройки безопасности диктуются не удобством агента).

## Что ломается первым

| Симптом | Причина | Настройка |
|---|---|---|
| Задание висит 10 минут | git или gh спрашивают логин/passphrase | `GIT_TERMINAL_PROMPT=0`, `ssh -o BatchMode=yes` |
| `Author identity unknown` | нет `user.name`/`user.email` | задать в global до первого коммита |
| `dubious ownership` | дерево принадлежит другому пользователю (контейнер, общий том) | `git config --global --add safe.directory <путь>`, а не `chmod -R 777` |
| Хост-ключ не принимается | первый коннект интерактивно спрашивает «yes/no» | заполнить known_hosts заранее, сверив отпечаток вне канала |
| `git log`/diff уходят в pager | pager ждёт ввода | `core.pager=cat`, `GIT_PAGER=cat` |
| Коммит агента не проходит хуки | хуки рассчитаны на человека (линтер всего дерева, 3 минуты) | `core.hooksPath` на свой каталог; тяжёлые проверки — отдельной командой, а не pre-commit |
| Пул-реквест не создаётся | у токена нет прав на запись | токен per-repo с минимальными правами, read по умолчанию |
| `git blame`/`bisect` врут | клон `--depth 1` или `--filter` | глубину ставить осознанно: см. ниже |

## Проверка машины

```bash
# Проверка машины под агента: падает с внятным списком, а не «что-то упало».
# Запускается из systemd-юнита, из префлайта агента и руками после обновления.
set -uo pipefail

fail=0
say() { printf '%s\n' "$*"; }
bad() { fail=$((fail + 1)); printf 'НЕТ: %s\n' "$*"; }

need_cmd() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    say "ok: $name"
  else
    bad "нет команды $name"
  fi
}

# Обязательный минимум. Версии тулчейнов проекта живут в его собственном
# AGENTS.md/README — здесь проверяется только «есть чем работать».
for c in git awk find df; do
  need_cmd "$c"
done

need_env() {
  local var="$1" why="$2"
  if [ -z "${!var:-}" ]; then
    bad "$var не задана: $why"
  else
    say "ok: $var"
  fi
}

# Неинтерактивность — не «удобно», а условие предсказуемости: зависший git
# держит лок и блокирует следующий прогон.
need_env GIT_TERMINAL_PROMPT "git не должен спрашивать логин"
need_env GIT_SSH_COMMAND "ssh обязан быть в BatchMode"
case "${GIT_SSH_COMMAND:-}" in
*"BatchMode=yes"*) say "ok: ssh в BatchMode" ;;
*) bad "GIT_SSH_COMMAND без BatchMode=yes" ;;
esac

# Идентичность: без неё первый же коммит пахнет «Author identity unknown».
git config --global user.email >/dev/null 2>&1 || bad "git user.email не задан"
git config --global user.name >/dev/null 2>&1 || bad "git user.name не задан"

# Пагера не должно быть: он читается как «команда ещё работает».
[ "$(git config --global core.pager 2>/dev/null || echo cat)" = "cat" ] ||
  bad "core.pager не cat: git будет ждать ввода"

# Ключи: сокет-агент или явный ключ на задачу, но не запароленный ключ без
# агента (passphrase = интерактивный вопрос).
if [ -n "${SSH_AUTH_SOCK:-}" ]; then
  say "ok: SSH_AUTH_SOCK задан"
elif [ -n "${SSH_KEY_FILE:-}" ] && [ -r "${SSH_KEY_FILE:-/nonexistent}" ]; then
  say "ok: SSH_KEY_FILE читается"
else
  bad "нет ни SSH_AUTH_SOCK, ни читаемого SSH_KEY_FILE"
fi

# Диск: агент, оставшийся без места, даёт странные ошибки (половина .git, битый
# index.lock), поэтому проверка идёт до работы, а не после падения.
free_mb=$(df -Pm "${WT_ROOT:-$HOME}" | awk 'NR==2 {print $4}')
[ "${free_mb:-0}" -ge 2048 ] || bad "свободно ${free_mb} МБ — на worktree может не хватить"

if [ "$fail" -gt 0 ]; then
  say "проверка не пройдена: $fail замечаний"
  exit 1
fi
say "машина готова"
```

## Worktree вместо «одной рабочей копии на всё»

```bash
# Один каталог на задачу. Общая копия на несколько задач — это гонка:
# переключение веток в одном дереве двумя процессами даёт подменённые файлы.
set -euo pipefail

WT_ROOT="${WT_ROOT:-$HOME/wt}"
MAIN="${MAIN:-$WT_ROOT/main}"          # bare-клон: в нём никто не работает

# Инициализация: partial clone вместо полного — быстрее и меньше диска.
# Цена: история по требованию тянется из сети, а с --depth ещё и bisect/blame
# работают по усечённой истории. Для агентских задач это обычно приемлемо,
# для «разберись в истории файла» — нет.
init_main() {
  local url="$1"
  mkdir -p "$WT_ROOT"
  git clone --filter=blob:none --no-checkout "$url" "$MAIN"
}

# add <ветка> — отдельное дерево под задачу. --track для существующей ветки,
# иначе новая ветка от актуального HEAD основной копии.
wt_add() {
  local branch="$1" path="$WT_ROOT/$1"

  # Имя ветки становится именем каталога: совпадение с основным клоном
  # означало бы «работаю прямо в основном клоне».
  if [ "$path" = "$MAIN" ]; then
    echo "имя задачи совпадает с основным клоном: $MAIN" >&2
    return 1
  fi
  [ -d "$path" ] && { echo "уже есть: $path" >&2; return 0; }

  mkdir -p "$WT_ROOT"
  if git -C "$MAIN" rev-parse --verify --quiet "origin/$branch" >/dev/null; then
    # --track + отправная точка: локальная ветка с заведённым upstream.
    git -C "$MAIN" worktree add --track -B "$branch" "$path" "origin/$branch"
  else
    # Новая ветка задачи. --no-track обязателен: без неё git заводит upstream на
    # ветку, с которой сделан отправной коммит (обычно main), и push с
    # push.default=upstream улетит в main.
    git -C "$MAIN" worktree add --no-track -B "$branch" "$path" "origin/HEAD"
  fi
  echo "$path"
}

# rm <ветка> — снять дерево и подчистить ссылки. Просто rm -rf оставляет
# «грязные» записи: следующие worktree list/start начинают ругаться.
wt_rm() {
  local path="$WT_ROOT/$1"
  git -C "$MAIN" worktree remove --force "$path" 2>/dev/null || rm -rf "$path"
  git -C "$MAIN" worktree prune
}

# Агенты оставляют деревья чаще, чем ветки: список старше N дней — на удаление.
# Сухой запуск по умолчанию; удаление явным флагом, чтобы «почистить» не
# превратилось в «потерял работу коллеги».
wt_aged() {
  local days="${1:-7}" apply="${2:-}"
  find "$WT_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"$days" ! -name main |
    while read -r dir; do
      echo "$dir"
      if [ "$apply" = "--apply" ]; then
        wt_rm "$(basename "$dir")"
      fi
    done
}
```

## Доступ: чем меньше, тем лучше

| Что | Как | Почему |
|---|---|---|
| Чтение чужих репо | deploy key read-only или fine-grained token на репо | угнанный ключ не открывает всю организацию |
| Запись в своё репо | отдельный ключ/токен на задачу, жизнь — до конца задачи | «ключ машины» живёт годами и состоит в нескольких репо |
| Кладём куда? | `credential.helper 'cache --timeout=3600'` (в памяти) | `store` — plaintext-файл; на общей машине это чужие доступы |
| Промпт за ключом | ключ без passphrase + `SSH_AUTH_SOCK`, либо ключ с passphrase и агент | passphrase в неинтерактивном прогоне = зависший процесс |
| Строгая проверка хостов | `known_hosts` заполнен заранее, отпечаток сверен вне канала | `StrictHostKeyChecking=no` — это не «временно», а MITM-окно |
| Права агента в репо | ветка + PR, а не push в основную | коммит агента обязан проходить те же проверки, что человеческий |

`GIT_SSH_COMMAND`, закрывающая большую часть таблицы:

```bash
# Неинтерактивный ssh для git: без вопросов, с таймаутом соединения и
# известным хостом. Экспортируется в окружение процесса агента, а не «вeach
# shell», который никто неsource-ит.
export GIT_TERMINAL_PROMPT=0
export GIT_PAGER=cat
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new"

# accept-new добавляет неизвестный хост без вопроса — компромисс: первый
# коннект не виснет, но подмена хоста на уже известном не пройдёт. Для
# известной инфраструктуры правильнее заполнить known_hosts заранее и оставить
# StrictHostKeyChecking=yes.
mkdir -p "$HOME/.ssh"
touch "$HOME/.ssh/known_hosts"

# git-окружение для автоматизации: никаких «спросить позже».
git config --global core.pager cat
git config --global advice.disabled true
git config --global pull.rebase false
git config --global init.defaultBranch main
git config --global fetch.prune true
```

## Уборка

```bash
# Обслуживание копии и деревьев: по таймеру, а не «когда диск кончился».
set -euo pipefail

MAIN="${MAIN:-$HOME/wt/main}"
WT_ROOT="${WT_ROOT:-$HOME/wt}"

maintain() {
  # FETCH_HEAD и refs разрастаются; prune удаляет удалённые ветки из локальных refs.
  git -C "$MAIN" fetch --all --prune --quiet

  # worktree prune чинит записи после удалённых «вручную» каталогов.
  git -C "$MAIN" worktree prune

  # Локальные ветки, у которых нет удалённой части и последняя запись старше
  # 30 дней: кандидаты на удаление. Список, а не молчаливое удаление.
  local now cutoff
  now=$(date +%s)
  cutoff=$((now - 30 * 86400))

  for branch in $(git -C "$MAIN" for-each-ref --format='%(refname:short) %(committerdate:unix)' \
      refs/heads | awk -v cut="$cutoff" '$2 < cut {print $1}'); do
    if ! git -C "$MAIN" rev-parse --verify --quiet "origin/$branch" >/dev/null; then
      echo "ветка без remote и старше 30 дней: $branch"
    fi
  done

  # Размер object-базы: чистить и репаковать стоит по факту роста, а не по
  # расписанию вслепую.
  git -C "$MAIN" count-objects -vH | awk '/^size-pack:/ {print "размер объектов:", $0}'
}

# git clean — единственная команда здесь, которая удаляет работу. Особенно
# приятно для агента: .env и ключи тоже «untracked». Поэтому флаг в списке
# параметров, а не «по умолчанию».
clean_tree() {
  local path="$1"
  case "$path" in
  "$WT_ROOT"/*) ;;
  *)
    echo "вне $WT_ROOT не убираю: $path" >&2
    return 1
    ;;
  esac
  git -C "$path" clean -fd -e '.env' -e '*.pem' -e 'secrets'
}
```

## Related

- [../agenting/rules.md](../agenting/rules.md) — границы того, что агенту разрешено менять
- [../agenting/snippets/lockfile.md](../agenting/snippets/lockfile.md) — один экземпляр прогона на машине
- [../agenting/patterns/coordinator-workers.md](../agenting/patterns/coordinator-workers.md) — worktree как способ развести параллельных воркеров
- [../cicd/github-actions.md](../cicd/github-actions.md) — когда вместо своей машины стоит взять hosted-раннер
- [commits.md](commits.md) — коммиты агента: тот же стандарт, что у человека
- [security.md](security.md) — где хранить доступы, если они на машине всё же нужны
