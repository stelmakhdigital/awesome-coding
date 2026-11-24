# CHANGELOG

Версии — git-теги `vN.N` (semver). Агенты пинят версию в `skills/awesome-coding/SKILL.md`.
Процесс релиза: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md), раздел «Релиз».

## v1.0 — 2026-11-24

Первый версионированный релиз. 15 разделов, 159 записей (78 сниппетов, 27 паттернов,
17 наборов правил, 12 таблиц решений, 16 концепций, 9 idioms). Код: 48 записей
проверены компилятором/запуском (`compiled`/`executed`), 60 — рецензией (`reviewed`).

### Контент

- Языки: Go 1.27, TypeScript 7.0, JavaScript ES2025, Python 3.14, C23, Bash 5.3,
  C# 14 / .NET 10, Kotlin 2.3, Unity 6.3 LTS (включая HLSL-шейдеры URP).
- Разделы: `shared` (15 кросс-языковых концепций), `database` (PostgreSQL 18, Redis 8),
  `messaging` (Kafka 4.3, RabbitMQ 4.3), `cicd` (GitHub Actions, GitLab CI, Docker,
  Kubernetes, секреты, матричные сборки), `architecture` (DDD tactical + strategic,
  7 архитектурных паттернов), `pm` (SDLC с discovery, PMBOK, требования, roadmap,
  PROJECT_MEMORY, риски).
- Секция «Безопасность» в `rules.md` всех 9 языков.

### Туллинг

- `make validate` — frontmatter, каталог `index/`, синхронизация README, ссылки.
- `make validate-mermaid`, `make search Q=…`, `make check-versions`, `make check-stale`.
- Каталог `index/` разбит по разделам: агент читает 23-127 строк вместо 942.
- Валидатор сверяет `tags` между frontmatter и `index/` и не даёт ставить
  `verified: none` на сниппет/паттерн с компилируемым кодом.

### Процессы

- `AGENTS.md` — роутер «задача → раздел»; `docs/FORMAT.md` — спецификация формата;
  `docs/adr/` — 3 ADR (agent-first, pinned versions, no-ORM в Go).
- `skills/awesome-coding/SKILL.md` — локальный кэш с пином на версию, поиск по
  тегам, лимит загрузки.

### Исправления

- `SKILL.md`: ветка обновления кэша не срабатывала никогда — `find … || git pull`
  полагался на код выхода `find`, который равен 0 и без находки. Проверяется вывод.
- `csharp/rules.md`, `csharp/idioms.md`: наборы тегов в frontmatter и `index/csharp.yaml`
  были разными — приведены к одному.
