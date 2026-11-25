# AGENTS.md — awesome-coding

Этот репозиторий — библиотека сниппетов, паттернов и правил для кодинг-агентов.
Каждая запись самодостаточна и имеет машиночитаемые метаданные (YAML frontmatter).

## Как пользоваться (роутинг)

**Шаг 1 — определите задачу:**

| Что делаете | Куда идти |
|---|---|
| Пишете код на конкретном языке | `<lang>/` (таблица ниже) |
| Веб-интерфейс: компоненты, состояние, тесты, сборка | `react/` (фреймворк поверх `typescript/`) |
| Принцип, общий для всех языков (ошибки, конкурентность, безопасность, тесты, API, observability, ревью, коммиты, рефакторинг, отладка, CLI) | `shared/` |
| Работа с данными: SQL, индексы, транзакции, миграции, кэш | `database/` (PostgreSQL, Redis) |
| Брокеры сообщений: Kafka, RabbitMQ | `messaging/` |
| Архитектура, DDD, уровни, bounded contexts, CQRS, event-driven | `architecture/` |
| Агент работает без человека: расписание, замок, чекпоинт, охотник за дефектами, координатор и воркеры | `agenting/` |
| CI/CD, Docker, Kubernetes, `gh`-автоматизация, интеграционные тесты со стеком | `cicd/` |
| Игра на Unity (кроссплатформа + Android), включая HLSL-шейдеры | `unity/` |
| Нативный Android (Kotlin) | `kotlin/` |
| Документирование проекта, ADR, диаграммы (mermaid) | `shared/documentation.md`, `shared/mermaid.md` |
| Управление проектом: SDLC, discovery, требования, roadmap, риски, PMBOK | `pm/` |
| Добавление записи в этот репозиторий (контрибьюция) | `docs/CONTRIBUTING.md`, `docs/FORMAT.md` |

**Шаг 2 — внутри раздела:**

1. `<section>/README.md` — версии и конвенции.
2. `<section>/rules.md` — обязательные guardrails (✅/❌), если секция его имеет
   (есть в: go, typescript, javascript, react, python, c, bash, csharp, kotlin, unity, database, agenting,
   messaging, cicd; нет в: shared, architecture, pm).
3. Конкретная запись — по тегам в `index/<section>.yaml` (поиск: `grep -i "тег" index/<section>.yaml`;
   без клона — GitHub code search по этому файлу или `make search Q=тег` после клона;
   синонимы, которых нет в тегах, — в `index/aliases.yaml`).
4. Выбор библиотеки/подхода — `<section>/decisions.md` (таблицы решений), если есть.

**Шаг 3 — приоритеты:** язык-специфика (`<lang>/`) важнее `shared/`, если запись явно не говорит об обратном.

## Языковые разделы

| Язык | Каталог | Версия |
|---|---|---|
| Go (референсный) | `go/` | 1.27 |
| TypeScript | `typescript/` | 7.0 |
| JavaScript | `javascript/` | ES2025 |
| React (веб-интерфейс) | `react/` | 19.3 |
| Python | `python/` | 3.14 |
| C | `c/` | C23 |
| Bash | `bash/` | 5.3 |
| C# | `csharp/` | .NET 10 (LTS) / C# 14 |
| Kotlin | `kotlin/` | 2.3 |
| Unity | `unity/` | 6.3 LTS (6000.3.x) |

## Жёсткие правила

- `rules.md` раздела — обязательный набор правил: соблюдайте ✅, избегайте ❌.
- Предпочитайте стандартную библиотеку, пока сниппет явно не рекомендует third-party.
- Код должен быть идиоматичным для закреплённой версии (таблица ниже).
- Не копируйте сниппеты вслепую: прочитайте секции «Когда использовать / Когда НЕ использовать».
- `verified` — факт прогона, а не обещание: уровень поднимают только после зелёного
  `make verify` (`make verify-fix` поднимает его сам и обновляет даты; что проверяет
  каждый язык — таблица в `docs/FORMAT.md`).
- Если подходящей записи нет — пишите код по правилам; при желании добавьте запись по `docs/FORMAT.md`.
- Коммиты — по [shared/commits.md](shared/commits.md) (общие правила) и
  [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) (специфика репо): один коммит — одна забота,
  `make validate` до коммита.
- Ревью кода — по [shared/code-review.md](shared/code-review.md): порядок проверок,
  серьёзность замечаний, чек-листы безопасности и производительности.

## Версии (проверено 2026-11-24, `make check-versions`)

| Технология | Версия | Fallback |
|---|---|---|
| Go | 1.27 | 1.26 |
| TypeScript | 7.0 | 6.x |
| JavaScript | ES2025 | ES2024 |
| React | 19.3 (19.3.1) | 18.3 |
| Vite | 8.3 (8.3.8) | 6.x |
| Vitest | 5.1 (5.1.1) | 3.x |
| Python | 3.14 | 3.13 |
| C | C23 (ISO 9899:2024) | C17 |
| Bash | 5.3 | 5.2 |
| C# | .NET 10 (LTS) / C# 14 | .NET 9 / C# 13 |
| Kotlin | 2.3 | 2.2 |
| Unity | 6.3 LTS (6000.3.x) | 6.0 LTS |
| PostgreSQL | 18 (18.6) | 17 |
| Redis | 8 (8.10.1) | 8.0 |
| Kafka | 4.3 (4.3.1) | 4.2 |
| RabbitMQ | 4.3 (4.3.5) | 4.0 |
| gh CLI | 2.105 | 2.9x |
| Caddy | 2.11 | 2.9 |

Перед добавлением новой записи проверьте, не вышла ли более новая стабильная версия.

**Итог квартальной проверки 2026-11-24** (`make check-versions`): пины оставлены.
Вышли Python 3.15, Kotlin 2.4.21, PostgreSQL 19.0, RabbitMQ 4.4.1 — смена пина
значит перепроверку затронутых записей (`make verify`), а не только таблицы;
свежевыпущенные мажоры (PostgreSQL 19) для библиотеки сниппетов хуже, чем
проверенный предыдущий. Go 1.27, TypeScript 7.0, .NET 10, Redis 8 — актуальны.
Следующая проверка — 2027-02.

## Структура

- `<lang>/` — языковой раздел: `README.md`, `rules.md`, `idioms.md`, `decisions.md`, `snippets/`, `patterns/`.
- `react/` — веб-интерфейс поверх TypeScript: `README.md`, `rules.md`, `decisions.md`, `snippets/`, `patterns/`. Идиомы языка — в `typescript/`, здесь не дублируются.
- `unity/` — игровые проекты (кроссплатформа + Android): та же структура + `shaders/` (HLSL); код не компилируется без Editor.
- `architecture/` — языконезависимая архитектура и DDD: `decisions.md`, `ddd/` (tactical + strategic), `patterns/`.
- `shared/` — кросс-языковые концепции (ошибки, конкурентность, безопасность,
  аутентификация, тесты, API, observability, время, конфигурация).
- `database/` — PostgreSQL + Redis: правила, решения, сниппеты.
- `messaging/` — брокеры: Kafka, RabbitMQ.
- `agenting/` — агентские автоматизации: `README.md`, `rules.md`, `decisions.md`, `snippets/`, `patterns/`. Про прогоны, где агента выпустили из цикла; оркестратор не закреплён намеренно.
- `cicd/` — GitHub Actions, GitLab CI, Docker, Kubernetes, `gh` в скриптах,
  интеграционные тесты на контейнерах.
- `pm/` — проектный/продуктовый менеджмент: SDLC, PMBOK, discovery, требования,
  риски + правила ведения `roadmap.md` и `PROJECT_MEMORY.md` в целевых проектах.
- `index/` — машиночитаемый каталог: `manifest.yaml` (шапка, версии) +
  `<section>.yaml` (записи раздела: теги, пути, статус, verified).
- `skills/awesome-coding/SKILL.md` — скилл для агентов (pi/dsh): кэш этого репо +
  роутинг разделов + лимит загрузок. Используется репо «через себя».
- `docs/FORMAT.md` — спецификация формата записей (для контрибьюторов).
- `docs/adr/` — архитектурные решения репозитория (ADR).
- `tools/validate.py` + `Makefile` — валидация (frontmatter, каталог, структура записей, текст, ссылки);
  `tools/verify_snippets.py` — прогон кода записей через тулчейны, `tools/readme.py` —
  генерация блока «Статус разделов», `tools/mcp_server.py` — поиск по каталогу
  для MCP-клиентов (`search`/`get`).

## Туллинг

```bash
make validate              # все проверки (frontmatter, каталог, индексы, структура, текст, алиасы, README, ссылки)
make validate-frontmatter  # только frontmatter
make validate-manifest     # только manifest
make validate-indexes      # README каталогов упоминают все файлы раздела
make validate-aliases      # index/aliases.yaml: форма ключей и существующие id
make validate-links        # только ссылки
make validate-mermaid      # синтаксис mermaid-блоков (node + cd tools && npm install)
make readme                # перегенерировать «Статус разделов» из index/*.yaml
make search Q="rate limit"   # поиск словами и фразами, от близких к далёким (tools/find.py)
make verify                # код-блоки через тулчейны в Docker (go/tsc/python/node/shellcheck/gcc/PG 18)
make verify-fix            # то же + поднять verified/updated, где прогон доказал
make check-versions        # сверка закреплённых версий с актуальными (сеть)
make check-stale           # записи с устаревшим frontmatter `updated` (квартальный аудит)
make test                  # тесты самого туллинга (вердикты раннеров, валидатор, поиск)
```

Перед коммитом — `make validate` (и `make test`, если правили `tools/`); меняли код в записи — ещё и
`python3 tools/verify_snippets.py --record <id>` (что проверяет каждый язык —
таблица в `docs/FORMAT.md`).

**Свежесть версий:** `.github/workflows/freshness.yml` по понедельникам гоняет
`make check-versions` и `make check-stale` и держит один open issue со списком
кандидатов (чистый прогон закрывает его). Решение за человеком: пин двигается
вместе с перепроверкой затронутых записей (`make verify`) и правкой таблицы
«Версии» + `updated` в `index/manifest.yaml`, а не одной правкой таблицы.

## Статусы записей

- `stable` — рекомендуемая, production-ready.
- `experimental` — новая или нестабильная, используйте осторожно.
- `deprecated` — оставлена для справки, в новом коде не использовать.
