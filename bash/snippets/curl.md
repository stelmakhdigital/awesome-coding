---
id: bash-curl
title: "Bash: curl в скриптах (ошибки, JSON, ретраи, загрузка)"
lang: bash
min_version: "5.2"
category: snippet
tags: [curl, http, networking, json, retry, download]
status: stable
updated: 2026-09-07
---

# curl в скриптах

**Когда использовать** — HTTP-запросы из bash-скриптов: API, загрузка файлов, health-check.
**Когда НЕ использовать** — сложная логика (мультишаговые сценарии, парсинг ответов): Python/Go; только `curl -v` в терминале — это не скрипт.

## Код

```bash
#!/usr/bin/env bash
set -euo pipefail

API="${API_BASE:?API_BASE не задан}"
TOKEN="${API_TOKEN:?API_TOKEN не задан}"

# GET: -f — ошибка на 4xx/5xx (exit != 0), -sS — тихо, но с ошибками.
get_item() {
  local id=$1
  curl -fsS --max-time 10 \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/json" \
    "$API/items/$id"
}

# POST JSON: тело собирает jq (никакой ручной конкатенации).
create_item() {
  local name=$1 price=$2
  curl -fsS --max-time 10 -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    --data-raw "$(jq -cn --arg n "$name" --argjson p "$price" '{name: $n, price_cents: $p}')" \
    "$API/items"
}

# Ответ в переменную + проверка статуса отдельно (когда нужен код ответа).
get_status() {
  local id=$1
  curl -sS -o /dev/null -w '%{http_code}' --max-time 10 \
    -H "Authorization: Bearer $TOKEN" \
    "$API/items/$id"
}

# Загрузка файла: ретраи + докачка (-C -) + атомарная запись (temp + mv).
download() {
  local url=$1 dest=$2
  local tmp
  tmp=$(mktemp "${dest}.XXXXXX")
  curl -fSL --retry 3 --retry-delay 2 --max-time 300 -C - -o "$tmp" "$url"
  mv "$tmp" "$dest"
}

# Health-check: успех/сбой без вывода тела.
health() {
  curl -fsS -o /dev/null --max-time 5 "$API/healthz"
}
```

## Правила

1. **`-fsS` — базовый набор для скриптов**: `-f` (HTTP-ошибка → exit 22), `-s` (без прогресса), `-S` (ошибки curl всё же печатаются). Без `-f` скрипт «успешно» получит тело 500.
2. **`--max-time` везде** — без него скрипт может зависнуть на вечном запросе.
3. **JSON-тело — через `jq`**: `--data-raw "$(jq -cn ...)"`; ручная конкатенация ломается на кавычках/спецсимволах.
4. **Секреты — в переменных окружения** (`${VAR:?}` — fail fast), не в аргументах/URL (попадают в `ps`, логи, историю).
5. **Загрузка — в temp + `mv`**: атомарная замена, нет «полфайла» при сбое.

## Pitfalls

- `--data` vs `--data-raw`: `--data` читает файл при значении `@file`; для литералов — `--data-raw` (явно).
- `-o /dev/null -w '%{http_code}'` — когда нужен именно код ответа; иначе `-f` проще.
- `-C -` (докачка) без `-L` на редиректах — проверяйте, что сервер поддерживает `Range`.
- TLS: для внутренних CA — `--cacert /path/to/ca.pem`; **не** `-k` (отключение верификации) в проде.
- Ответ в переменную: `body=$(get_item 1)` — при `set -e` сбой запроса остановит скрипт (это правильно).
- `jq` обязателен в зависимостях (`brew install jq` / `apt install jq`) — проверяйте `command -v jq`.

## Related

- [error-handling.md](error-handling.md)
- [files.md](files.md)
- [decisions.md](../decisions.md)
