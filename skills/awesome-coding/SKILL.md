---
name: awesome-coding
description: "Библиотека проверенных сниппетов, паттернов и правил для кодинг-агентов: Go, TypeScript, JavaScript, Python, C, Bash, C#, Kotlin, Unity + PostgreSQL/Redis, Kafka/RabbitMQ, CI/CD, PM. Локальный кэш (git clone), поиск по тегам/полнотексту, офлайн-фолбэк."
whenToUse: "Перед написанием, ревью или рефакторингом кода на Go/TS/JS/Python/C/Bash/C#/Kotlin/Unity, при работе с PostgreSQL, Redis, Kafka, RabbitMQ, CI/CD, архитектурой (DDD) или проектным менеджментом."
---

# awesome-coding — локальная библиотека сниппетов и правил

Источник: репозиторий `stelmakhdigital/awesome-coding` (этот же репо, если скилл
живёт внутри него — кэш тогда может быть и самим рабочим каталогом репо).

## Workflow

### 1. Кэш (идемпотентно, ≤1 команда)

```bash
k=~/.cache/awesome-coding
[ -d "$k/.git" ] || git clone --depth 1 https://github.com/stelmakhdigital/awesome-coding "$k"
find "$k/index/manifest.yaml" -mtime -7 2>/dev/null || git -C "$k" pull --ff-only
```

- Первый запуск — клон (~1.4 МБ). Дальше — 0 работы.
- Кэш старше 7 дней — `git pull`. **Сети нет или pull упал — молча работаем со
  старым кэшем**, задачу не блокируем.
- Если текущий проект и есть awesome-coding — `k` = корень репо, шаги пропускать.

### 2. Разделы под задачу (1–3, не «все»)

Язык проекта — по маркерам:

| Маркер | Раздел |
|---|---|
| `go.mod` | `go` |
| `package.json` (+`tsconfig.json`) | `typescript` |
| `package.json` (без tsconfig) | `javascript` |
| `pyproject.toml`, `requirements.txt` | `python` |
| `Makefile` + `*.c`/`*.h` | `c` |
| `*.sh` / shell-скрипты | `bash` |
| `*.csproj` | `csharp` |
| `ProjectVersion.txt` | `unity` |
| `*.kt`, `build.gradle.kts` | `kotlin` |

Домен задачи — дополнительные разделы:

| Домен | Раздел |
|---|---|
| SQL, индексы, транзакции, кэш, Redis | `database` |
| Kafka, RabbitMQ, очереди | `messaging` |
| CI/CD, Docker, K8s | `cicd` |
| DDD, уровни, bounded contexts, CQRS | `architecture` |
| SDLC, roadmap, риски, PMBOK | `pm` |
| принцип, общий для языка (ошибки, тесты, безопасность, ревью) | `shared` |

Подробный роутинг — в `$k/AGENTS.md` (таблицы там же).

### 3. Поиск (индекс → полнотекст)

```bash
# 1) по тегу/названию в индексе нужных разделов (150 строк, мгновенно):
grep -i "retry" "$k"/index/go.yaml "$k"/index/shared.yaml

# 2) не нашлось — полнотекст по каталогам разделов:
rg -l -i "retry" "$k/go" "$k/shared" -g '*.md'
```

Из индекса берёте `path` + `status`/`verified` одним взглядом.

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
