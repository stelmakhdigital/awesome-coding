# CHANGELOG

Версии — git-теги `vN.N` (semver). Агенты пинят версию в `skills/awesome-coding/SKILL.md`.
Процесс релиза: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md), раздел «Релиз».

## v1.1 — 2026-11-24

Тулчейк проверки кода, раздел `llm/`, недостающие guardrails; `verified` — по факту прогона.

### Туллинг

- `tools/verify_snippets.py` + `make verify` / `make verify-fix` — код-блоки записей
  прогоняются реальными тулчейнами в Docker (go build+vet, tsc --strict, Python 3.14
  compile, node --check, shellcheck, gcc -std=c23). `verified` поднимается по итогам
  прогона и никогда не понижается. В CI — отдельный job по языкам.
- `tools/ac.py` — общий разбор формата (frontmatter, каталог, код-блоки): валидатор,
  поиск, audit и верификатор читают формат из одного места.
- `tools/readme.py` — блок «Статус разделов» генерируется из каталога
  (`make readme`; в `make validate` — проверка, что блок не разошёлся).
  Счётчики руками больше не ведутся.
- `tools/mcp_server.py` — MCP-сервер поверх каталога: `search` идёт по каталогу,
  полный текст отдаёт только для запрошенной записи. Поиск по библиотеке без клона.
- Проверка `text`: CJK-символы и смешение раскладок («batч», «Кrash»).

### Контент

- Раздел `llm/` — приложения с моделью: правила (таймаут, ретраи, бюджет, версия
  промпта, путь деградации, что писать в логи), таблицы решений, `evals.md` и два
  сниппета одного слоя вызова (Go на stdlib, Python на httpx).
- `messaging/rules.md` — доставка и дедупликация, DLQ и backoff, порядок сообщений,
  схема события, настройки брокера (acks, min.insync.replicas, quorum-очереди).
- `cicd/rules.md` — кеш по lockfile, permissions, build once, actions по SHA, OIDC,
  multi-stage, probes и graceful shutdown, миграции вне пода.
- `shared/authentication.md` — пароли, сессии против токенов, JWT, MFA: цена решения
  видна до выбора библиотеки.
- `go/snippets/rate-limit.md` — token bucket на ключ с eviction, 429 с Retry-After,
  ограничение параллельности наружу.
- `c/snippets/strings.md`: `stdstring.h` и `cstr_*` — в C23 такой библиотеки нет
  (границы — план C2y). Переписано: `snprintf` с проверкой усечения, `memcpy` с
  терминатором, `strstr`/`strncmp`, растущий буфер. Блоки собираются и выполняются.
- `architecture/patterns/layered.md` — добавлен пакет `domain`, запись собирается целиком.
- 12 мест со словами в чужой раскладке (cicd, csharp, database, typescript, unity).

### Каталог

- Записей: 168 (было 159). «Статус разделов» пересобран из каталога.
- `compiled` было 19, стало 50: 28 записей подняты прогоном `make verify`, ещё 3 —
  новые записи. `reviewed` 60 → 35, `executed` 29 без изменений.
- Правило валидатора: у сниппета/паттерна с код-блоком компилируемого языка нельзя
  поставить `verified: none`. На v1.0 таких записей было три.

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
