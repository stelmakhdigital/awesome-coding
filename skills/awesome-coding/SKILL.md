---
name: awesome-coding
description: "Библиотека проверенных сниппетов, паттернов и правил для кодинг-агентов: Go, TypeScript, JavaScript, Python, C, Bash, C#, Kotlin, Unity + PostgreSQL/Redis, Kafka/RabbitMQ, CI/CD, PM. Локальный кэш (git clone), поиск по тегам/полнотексту, офлайн-фолбэк."
whenToUse: "Перед написанием, ревью или рефакторингом кода на Go/TS/JS/Python/C/Bash/C#/Kotlin/Unity, при работе с PostgreSQL, Redis, Kafka, RabbitMQ, CI/CD, архитектурой (DDD) или проектным менеджментом."
updated: 2026-11-24
---

# awesome-coding — локальная библиотека сниппетов и правил

Источник: репозиторий `stelmakhdigital/awesome-coding` (этот же репо, если скилл
живёт внутри него — кэш тогда может быть и самим рабочим каталогом репо).

## Workflow

### 1. Кэш (идемпотентно, ≤1 команда)

```bash
ac=v1.11                                   # пин версии библиотеки (обновляется при релизе)
r=https://github.com/stelmakhdigital/awesome-coding
k=~/.cache/awesome-coding
[ -d "$k/.git" ] || git -c advice.detachedHead=false clone -q --depth 1 --branch "$ac" "$r" "$k"
# find ниже выдаёт путь, если файл свежее 7 дней (exit у него всегда 0 — проверять вывод)
[ -n "$(find "$k/index/manifest.yaml" -mtime -7 2>/dev/null)" ] || {
  git -C "$k" fetch -q --depth 1 origin tag "$ac" && git -C "$k" checkout -q "$ac"
} 2>/dev/null || true
```

- Первый запуск — клон на пин (~1.4 МБ). Дальше — 0 работы.
- Кэш старше 7 дней — подтянуть тот же пин (переклон не нужен, сети почти нет).
  Не `find … || git pull`: `find` выходит с кодом 0 и без находки, ветка `||` не
  сработала бы никогда — проверяется вывод.
- **Сети нет или fetch упал — молча работаем со старым кэшем**, задачу не блокируем.
- Кэш всегда на известной версии: `git -C "$k" describe --tags` — какой ровно набор
  правил вы применили. При проблемах в выводах сверяйте пин с `CHANGELOG.md`.
- Если текущий проект и есть awesome-coding — `k` = корень репо, шаги пропускать.

### 2. Разделы под задачу (1–3, не «все»)

Язык проекта — по маркерам:

| Маркер | Раздел |
|---|---|
| `go.mod` | `go` |
| `package.json` (+`tsconfig.json`) | `typescript` |
| `package.json` (без tsconfig) | `javascript` |
| `package.json` + `react` в зависимостях | `react` (+ `typescript`) |
| `pyproject.toml`, `requirements.txt` | `python` |
| `Makefile` + `*.c`/`*.h` | `c` |
| `*.sh` / shell-скрипты | `bash` |
| расписание с агентом внутри (`.github/workflows/*` c `schedule`, cron, systemd timer) | `agenting` |
| `*.csproj` | `csharp` |
| `ProjectVersion.txt` | `unity` |
| `*.kt`, `build.gradle.kts` | `kotlin` |

Домен задачи — дополнительные разделы:

| Домен | Раздел |
|---|---|
| SQL, индексы, транзакции, кэш, Redis | `database` |
| Kafka, RabbitMQ, очереди | `messaging` |
| CI/CD, Docker, K8s, `gh` в скриптах, интеграционные тесты | `cicd` |
| DDD, уровни, bounded contexts, CQRS | `architecture` |
| SDLC, roadmap, риски, PMBOK | `pm` |
| принцип, общий для языка (ошибки, тесты, безопасность, ревью) | `shared` |

Подробный роутинг — в `$k/AGENTS.md` (таблицы там же).

### 3. Поиск (индекс → полнотекст)

```bash
# 0) есть python3 + PyYAML — ранжированный поиск с синонимами (best first):
python3 "$k"/tools/search.py "upsert"

# 1) нет python — по тегу/названию в индексе нужных разделов (150 строк, мгновенно):
grep -i "retry" "$k"/index/go.yaml "$k"/index/shared.yaml

# 2) не нашлось — полнотекст по каталогам разделов:
rg -l -i "retry" "$k/go" "$k/shared" -g '*.md'
```

Из индекса берёте `path` + `status`/`verified` одним взглядом. Синонимы, которых
нет в тегах записей («upsert» при теге `on-conflict»), — в `$k/index/aliases.yaml`;
известные слова ищутся и по ним.

Если в сессии уже подключён MCP-сервер `awesome-coding` (`python3 $k/tools/mcp_server.py`),
первые два шага заменяются одним вызовом: `search(query, section)`, затем `get(id)`
по выбранной записи. Текст и там, и там читается из кэша — сеть не нужна.

### 4. Загрузка (жёсткий лимит ≤5 файлов)

Порядок:

1. `<lang>/rules.md` — **обязательно**, если язык затронут (guardrails ✅/❌).
2. 1–3 найденные записи — перед копированием кода читать «Когда использовать /
   Когда НЕ использовать».
3. `<lang>/decisions.md` — только если стоит выбор библиотеки/подхода.

Приоритет: язык-специфика (`<lang>/`) важнее `shared/`.

### 5. Пусто — и дальше

Записей нет → пишите код по `rules.md` / идиоматике закреплённой версии (версии —
в `$k/index/manifest.yaml`). Не приписывайте библиотеке то, чего там нет.

## Правила применения

- `status: stable` — использовать; `experimental` — осторожно; `deprecated` — только
  для справки.
- Предпочитать stdlib, пока запись явно не рекомендует third-party.
- Код — идиоматичный для версии из `min_version` записи и `manifest.yaml`.
