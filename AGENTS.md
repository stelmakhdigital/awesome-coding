# AGENTS.md — awesome-coding

Этот репозиторий — библиотека сниппетов, паттернов и правил для кодинг-агентов.
Каждая запись самодостаточна и имеет машиночитаемые метаданные (YAML frontmatter).

## Как пользоваться (роутинг)

**Шаг 1 — определите задачу:**

| Что делаете | Куда идти |
|---|---|
| Пишете код на конкретном языке | `<lang>/` (таблица ниже) |
| Принцип, общий для всех языков (ошибки, конкурентность, безопасность, тесты, API, observability, ревью, коммиты) | `shared/` |
| Работа с данными: SQL, индексы, транзакции, миграции, кэш | `database/` (PostgreSQL, Redis) |
| Брокеры сообщений: Kafka, RabbitMQ | `messaging/` |
| Архитектура, DDD, уровни, bounded contexts, CQRS, event-driven | `architecture/` |
| CI/CD, Docker, Kubernetes | `cicd/` |
| Игра на Unity (кроссплатформа + Android), включая HLSL-шейдеры | `unity/` |
| Нативный Android (Kotlin) | `kotlin/` |
| Документирование проекта, ADR, диаграммы (mermaid) | `shared/documentation.md`, `shared/mermaid.md` |
| Добавление записи в этот репозиторий (контрибьюция) | `docs/CONTRIBUTING.md`, `docs/FORMAT.md` |

**Шаг 2 — внутри раздела:**

1. `<section>/README.md` — версии и конвенции.
2. `<section>/rules.md` — обязательные guardrails (✅/❌), если секция его имеет
   (есть в: go, typescript, javascript, python, c, bash, csharp, kotlin, unity, database;
   нет в: shared, messaging, cicd, architecture).
3. Конкретная запись — по тегам в `index/manifest.yaml` (поиск: `grep -i "тег" index/manifest.yaml`;
   без клона — GitHub code search по этому файлу или `make search Q=тег` после клона).
4. Выбор библиотеки/подхода — `<section>/decisions.md` (таблицы решений), если есть.

**Шаг 3 — приоритеты:** язык-специфика (`<lang>/`) важнее `shared/`, если запись явно не говорит об обратном.

## Языковые разделы

| Язык | Каталог | Версия |
|---|---|---|
| Go (референсный) | `go/` | 1.27 |
| TypeScript | `typescript/` | 7.0 |
| JavaScript | `javascript/` | ES2025 |
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
- Если подходящей записи нет — пишите код по правилам; при желании добавьте запись по `docs/FORMAT.md`.
- Коммиты — по [shared/commits.md](shared/commits.md) (общие правила) и
  [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) (специфика репо): один коммит — одна забота,
  `make validate` до коммита.
- Ревью кода — по [shared/code-review.md](shared/code-review.md): порядок проверок,
  серьёзность замечаний, чек-листы безопасности и производительности.

## Версии (закреплено и проверено на 2026-09-06)

| Технология | Версия | Fallback |
|---|---|---|
| Go | 1.27 | 1.26 |
| TypeScript | 7.0 | 6.x |
| JavaScript | ES2025 | ES2024 |
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

Перед добавлением новой записи проверьте, не вышла ли более новая стабильная версия.

## Структура

- `<lang>/` — языковой раздел: `README.md`, `rules.md`, `idioms.md`, `decisions.md`, `snippets/`, `patterns/`.
- `unity/` — игровые проекты (кроссплатформа + Android): та же структура + `shaders/` (HLSL); код не компилируется без Editor.
- `architecture/` — языконезависимая архитектура и DDD: `decisions.md`, `ddd/` (tactical + strategic), `patterns/`.
- `shared/` — кросс-языковые концепции (ошибки, конкурентность, безопасность, тесты, API, observability, время, конфигурация).
- `database/` — PostgreSQL + Redis: правила, решения, сниппеты.
- `messaging/` — брокеры: Kafka, RabbitMQ.
- `cicd/` — GitHub Actions, GitLab CI, Docker, Kubernetes.
- `index/manifest.yaml` — машиночитаемый каталог всех записей (теги, пути, статус, verified).
- `docs/FORMAT.md` — спецификация формата записей (для контрибьюторов).
- `docs/adr/` — архитектурные решения репозитория (ADR).
- `tools/validate.py` + `Makefile` — валидация (frontmatter, manifest, ссылки).

## Туллинг

```bash
make validate              # все проверки (frontmatter + manifest + ссылки)
make validate-frontmatter  # только frontmatter
make validate-manifest     # только manifest
make validate-links        # только ссылки
make validate-mermaid      # синтаксис mermaid-блоков (node + cd tools && npm install)
make search Q=async        # поиск записей в manifest по тегу/названию
make check-versions        # сверка закреплённых версий с актуальными (сеть)
```

Перед коммитом новых записей запустите `make validate`.

**Свежесть версий:** раз в квартал — `make check-versions`; при ⚠️ обновите таблицу «Версии»
(проверив фолбэк), заголовок `updated` в `index/manifest.yaml` и перепроверьте затронутые сниппеты.

## Статусы записей

- `stable` — рекомендуемая, production-ready.
- `experimental` — новая или нестабильная, используйте осторожно.
- `deprecated` — оставлена для справки, в новом коде не использовать.
