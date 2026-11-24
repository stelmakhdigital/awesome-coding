# CHANGELOG

Версии — git-теги `vN.N` (semver). Агенты пинят версию в `skills/awesome-coding/SKILL.md`.
Процесс релиза: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md), раздел «Релиз».

## v1.3 — 2026-11-24

Две записей, которых в библиотеке не было (пагинация, трейсинг), и проверка,
которая держит формат записи.

### Контент

- `database/snippets/pagination.md` — keyset против OFFSET: сравнение кортежей с
  tie-break по уникальной колонке, индекс под порядок сортировки, `LIMIT N+1` вместо
  `COUNT(*)`, непрозрачный курсор в Go с `ErrBadCursor` вместо «пустой страницы без
  объяснения», размер страницы задаёт сервер.
- `go/snippets/tracing.md` — OpenTelemetry: OTLP/HTTP экспорт, ParentBased-сэмплирование,
  span с корректным статусом ошибки, `traceparent` на вход и на выход, shutdown
  трейсера; в ловушках — кардинальность имён спанов и секреты в атрибутах.
- `shared/api-design.md` и `shared/observability.md` теперь ссылками ведут на эти
  записи, а не оставляют читателя с одним описанием.

### Туллинг

- Проверка `structure`: у `category: snippet` требуются «Когда использовать»,
  «Когда НЕ использовать» и `Related`, у `pattern` — «Когда использовать» и
  `Related`. Каталог проходит её без правок — правило фиксирует существующую
  договорённость, а не заводит долг.
- `make check-versions` больше не велит «обновить таблицу»: смена пина — решение
  человека. Итог сверки 2026-11-24 записан в AGENTS.md (вышли Python 3.15,
  Kotlin 2.4.21, PostgreSQL 19.0, RabbitMQ 4.4.1 — пины оставлены, следующая
  проверка 2027-02).

### Каталог

- Записей: 170 (было 168). Код проверен: 83 из 112 записей с кодом
  (`compiled` 54, `executed` 29).
- `make verify`: 119 прогонов `ok`, 3 `deps` (grpc-стабы, соседние DDD-пакеты),
  9 `fragment` (иллюстрации в `go/idioms.md` и концепциях `shared/`).

## v1.2 — 2026-11-24

Код из библиотеки проверяется шире: собраны сниппеты брокеров и БД, добавлена
проверка SQL; CI приведён к собственным правилам.

### Туллинг

- `make verify` умеет SQL: поднимает `postgres:18-alpine` (закреплённая версия) и
  выполняет блоки записи по порядку в одной схеме. `deps` — не хватает таблиц или
  параметров `$1`; `fail` — настоящая ошибка. Раздел `database` ушёл из примечания
  «вне make verify».
- Проверка `text` (CJK и смешение раскладок) подключена к `make validate`: раньше
  она существовала, но цель `validate` её не вызывала, и в CI она не запускалась.
  Код и inline-`код` из проверки исключены, номера строк в отчёте совпадают с файлом.
- `make verify` ломает сборку и на `fmt`, не только на `fail`; в отчёте о непокрытых
  языках больше нет `text`/`console`/`diff`.
- `tools/ac.py`: отсутствие PyYAML — внятная ошибка вместо traceback (важно для
  MCP-сервера на машине агента).

### Контент

- Сниппеты `messaging` (Kafka producer, consumer groups, RabbitMQ, outbox) и
  `database` (redis, n+1) дописаны до собираемых файлов. Реальные расхождения с API,
  которые это нашло: `&kafka.Reader{...}` (нужен `kafka.NewReader(kafka.ReaderConfig{...})`),
  `WaitForConfirms*` в amqp091-go v1.17 (подтверждение берут с `PublishWithDeferredConfirm…`),
  `x-delivery-limit` без quorum-очереди, коммит после неудачной отправки в DLQ,
  `publishBatch` в outbox, который был комментарием.
- SQL-примеры `database` выполняются: добавлены схемы примеров, псевдо-SQL
  (`INSERT INTO a (...) VALUES (...)`) конкретизирован.
- `cicd`: `Вolumes`, `эвictions`, `дigest`, `тегуmajor`; `unity`: иероглифы вместо
  «бюджетных»; всего 12 мест со словами в чужой раскладке.

### Каталог

- Записей те же 168. Код проверен: 81 запись из 110 с кодом (`compiled` 52,
  `executed` 29); `deps` — 3 (grpc-стабы и соседние DDD-пакеты), `fragment` — 9
  (иллюстративные блоки в `go/idioms.md` и концепциях `shared/`).

### Процессы

- CI по правилам из `cicd/rules.md`: сторонние actions закреплены по SHA
  (checkout v7.0.1, setup-python v7.1.0, setup-node v7.1.0), обновляет их dependabot
  (`.github/dependabot.yml`); `permissions: contents: read`; `concurrency` по ref;
  npm-зависимости через `npm ci` с кешем по lockfile.
- Скилл: клон кэша работает тихо (`-q`, без detached-HEAD совета) — агент больше не
  получает стену текста на ровном месте.

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
- Проверка `text`: CJK-символы и смешение раскладок («`batч`», «`Кrash`»).

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
