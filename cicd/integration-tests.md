---
id: cicd-integration-tests
title: "CI: интеграционные тесты на реальном стеке контейнеров"
lang: bash
min_version: "2.31"
category: snippet
tags: [integration-tests, docker-compose, healthcheck, ci, github-actions, teardown, artifacts, port-conflict]
status: stable
updated: 2026-11-25
---

# CI: интеграционные тесты на реальном стеке контейнеров

**Когда использовать** — тест проверяет поведение вместе с зависимостью: SQL против Postgres, кэш против Redis, очередь против брокера, HTTP-вызов против заглушки, которая ведёт себя как настоящая (редиректы, таймауты, 429). Тот же стек должен подниматься локально одной командой — иначе тесты CI и тесты разработчика расходятся, и CI становится «местом, где падает».
**Когда НЕ использовать** — логику можно проверить без контейнера (юнит-тест с fake-реализацией быстрее и не врёт про инфраструктуру); зависимость не поднимается в контейнере (тогда договор проверяют контракты); тесту нужна среда whole-cluster (это отдельный прогон по расписанию, а не каждый push).

## Два способа поднять зависимость

| | `services:` в определении job'а | свой `compose.yaml` |
|---|---|---|
| Сколько писать | несколько строк, healthcheck руками | файл, который живёт в репозитории |
| Совпадение с локальным запуском | нет: локально поднимают как хотят | одно и то же место: CI и разработчик |
| Сложная топология (несколько сетей, build приложения, тома миграций) | упирается | нормальная работа |
| Параллельные job'ы на одном раннере | порты заняты — конфликт | лечится `-p` и `expose` вместо `ports` |
| Отладка упавшего теста | пересоздать job | `docker compose logs`, та же команда локально |

Правило выбора: одна зависимость и тест ходит по `localhost` — `services:`. Зависимостей несколько или стек нужен локально — compose-файл в репозитории, и CI вызывает ровно ту команду, что и человек.

## Ждать готовности, а не порта

```bash
# Поднять стек и дождаться готовности. Порт открывается раньше, чем сервис
# готов принимать соединения: Postgres слушает 5432 до конца восстановления
# журнала, приложение отвечает 503 во время миграций. healthcheck обязан
# проверять то, без чего тест бессмыслен, — запрос, а не «порт отвечает».
set -euo pipefail

COMPOSE="${COMPOSE:-docker compose}"
PROJECT="${PROJECT:-ci-${GITHUB_RUN_ID:-local}-$$}"     # уникальность: параллельные job'ы на одном раннере
TIMEOUT="${TIMEOUT:-120}"

up() {
  # --wait работает только у сервисов с healthcheck'ом и падает кодом возврата,
  # когда хоть один не стал healthy: проверять «поднялось» после него не нужно.
  $COMPOSE -p "$PROJECT" up -d --wait --wait-timeout "$TIMEOUT"
}

# Когда healthcheck'а нет (образ не предусматривает) — ждём осмысленный сигнал,
# а не «порт отвечает». TCP-коннект к Postgres ничего не обещает: сервер ещё не
# принял соединения.
wait_ready() {
  local service="$1" deadline=$((SECONDS + TIMEOUT)) status

  while [ "$SECONDS" -lt "$deadline" ]; do
    status=$($COMPOSE -p "$PROJECT" ps --format '{{.Service}} {{.State}} {{.Health}}' 2>/dev/null |
      awk -v s="$service" '$1 == s {print $3}')
    case "$status" in
    healthy) return 0 ;;
    unhealthy)
      echo "$service: unhealthy" >&2
      return 1
      ;;
    esac
    sleep 2
  done

  echo "$service: не готов за ${TIMEOUT}s (последний статус: ${status:-нет})" >&2
  return 1
}

# Падение должно быть читаемым: без логов разбор начинается с пересоздания job'а.
dump_logs_on_failure() {
  local dir="${1:-ci-artifacts}"
  mkdir -p "$dir"
  $COMPOSE -p "$PROJECT" logs --no-color >"$dir/compose.log" 2>&1 || true
  $COMPOSE -p "$PROJECT" ps --format '{{.Service}} {{.State}} {{.Health}}' \
    >"$dir/compose-ps.txt" 2>&1 || true
  echo "логи: $dir" >&2
}

# Тома остаются на раннере и отравливают следующий прогон (старые данные,
# старые миграции). Уникальный project + съём томов обязателны.
down() {
  $COMPOSE -p "$PROJECT" down -v --remove-orphans
}
```

## Данные: миграции, сид, изоляция

```bash
# Состояние базы перед тестами. Два подхода и цена каждого.
set -euo pipefail

COMPOSE="${COMPOSE:-docker compose}"
PROJECT="${PROJECT:-ci}"

# 1. Миграции при старте контейнера (init-скрипты, goose/go-migrate в entrypoint).
#    Быстро и совпадает с прод-запуском. Риск: тест, который рассчитывает на
#    пустую базу, начинает зависеть от порядка миграций.
migrate_up() {
  $COMPOSE -p "$PROJECT" exec -T app migrate up
}

# 2. Схема в temp-schema + пересоздание между тестами.
#    Медленнее, зато тесты не видят данных друг друга. Схема Postgres — самый
#    дешёвый «чистый мир» на живом сервере: пересоздать схему дешевле, чем
#    поднимать сервер.
reset_schema() {
  local schema="$1"
  $COMPOSE -p "$PROJECT" exec -T postgres \
    psql -U postgres -v ON_ERROR_STOP=1 -c "DROP SCHEMA IF EXISTS $schema CASCADE; CREATE SCHEMA $schema;"
}

# 3. Транзакция + rollback вокруг каждого теста: самый быстрый вариант, но
#    проверяет только то, что не видит различий между «в транзакции» и «в мире»
#    (sequence, триггеры на commit, параллельные соединения).
#    Выбор — по тому, что тест проверяет, а не по скорости.

# Сид-данные — отдельным файлом и отдельной командой, а не «в fixture'ах кода»:
# локально сид должен подниматься без сборки приложения.
seed() {
  $COMPOSE -p "$PROJECT" exec -T postgres \
    psql -U postgres -v ON_ERROR_STOP=1 -f - <"test/seed.sql"
}
```

## GitHub Actions: job с сервисами

```yaml
# Один job, одна зависимость, минимум файлов. Проверка готовности — health
# команды, а не sleep: sleep либо медленнее, либо всё равно гонка.
name: integration

on:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: integration-${{ github.ref }}
  cancel-in-progress: true

jobs:
  itest:
    runs-on: ubuntu-24.04

    services:
      postgres:
        image: postgres:18-alpine
        env:
          POSTGRES_PASSWORD: ci-not-a-secret
          POSTGRES_DB: app_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "psql -U postgres -d app_test -Atc 'select 1'"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-go@v5
        with:
          go-version: "1.27"

      - name: Миграции
        run: go run ./cmd/migrate up
        env:
          DATABASE_URL: postgres://postgres:ci-not-a-secret@localhost:5432/app_test?sslmode=disable

      - name: Тесты
        run: go test -tags=integration -count=1 ./tests/...
        env:
          DATABASE_URL: postgres://postgres:ci-not-a-secret@localhost:5432/app_test?sslmode=disable

      # Проверка готовности — запрос, а не pg_isready: pg_isready зелёный и с
      # несуществующими пользователем и базой.
      - name: Логи базы при падении
        if: failure()
        run: docker logs "${{ job.services.postgres.id }}" >pg.log || true
```

## Что ломается чаще всего

| Симптом | Причина | Что делать |
|---|---|---|
| Тесты падают на CI, локально проходят | ждали порт вместо готовности | `healthcheck` + `up --wait`, либо свой опрос осмысленного сигнала |
| `port is already allocated` | второй job на том же раннере занял порт | уникальный `-p`, `expose` вместо `ports`, тесты внутри сети compose |
| Следующий прогон видит данные прошлого | том пережил job | `down -v`, уникальный project, temp-схема между тестами |
| `--wait` завис/упал сразу | у сервиса нет healthcheck'а | добавить `healthcheck` в compose, либо опрос своей проверкой |
  | healthcheck зелёный, тесты падают на первой таблице | `pg_isready` проверяет, что постмастер принимает соединения: `-U nosuch -d nope` тоже даёт healthy | проверка = осмысленный запрос (`psql -c 'select 1'`), а не «порт отвечает» |
| Тесты мешают друг другу | параллельные тесты в одной базе | temp-схема или транзакция + rollback на тест, `t.Parallel()` только с изоляцией |
| 40 минут на прогон, где тесты идут 3 | тянут образы и собирают заново | кеш образов (`cache-type=buildx`/registry mirror), `pull_policy`, не собирать приложение в compose для каждого прогона |
| Упало — непонятно что | логи остались в контейнере, контейнер удалён | писать логи в артефакт до `down`, `if: failure()` |
| Секрет в `docker compose logs` | пароль в `environment` попадает в вывод | секреты через `.env`/OIDC, логи — как публичные данные ([rules.md](rules.md)) |

## Related

- [docker.md](docker.md) — compose-файл, тома, healthcheck'и
- [github-actions.md](github-actions.md) — job'ы, кеш, условия шагов
- [rules.md](rules.md) — правила раздела: секреты, читаемые падения, границы времени
- [../database/snippets/dialect-portability.md](../database/snippets/dialect-portability.md) — если «тестовая база» расходится с боевой
- [../go/snippets/testing.md](../go/snippets/testing.md) — build-теги для интеграционных тестов, чтобы они не бегали в `go test ./...`
- [../agenting/snippets/watchdog.md](../agenting/snippets/watchdog.md) — общий бюджет времени на прогон стека
