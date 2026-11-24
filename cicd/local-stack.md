---
id: cicd-local-stack
title: "Локальный стек: compose + обратный прокси с внутренним TLS"
lang: bash
min_version: "2.11"
category: snippet
tags: [local-stack, docker-compose, caddy, https, internal-ca, reverse-proxy, healthcheck, sse, secure-context]
status: stable
updated: 2026-11-24
---

# Локальный стек: compose + обратный прокси с внутренним TLS

**Когда использовать** — приложение живёт только на машине разработчика и агента, но требует того, что упрощённый `localhost:8080` не даёт: HTTPS для браузера (микрофон, камера, cookies `Secure`, `crypto.subtle` работают только в защищённом контексте), один вход для фронта и API без CORS-костылей, заголовки `X-Forwarded-*` как в проде, поток ответа без буферизации.
**Когда НЕ использовать** — один статичный файл без бэкенда; нужен боевой ingress/TLS от Let's Encrypt (это другая запись и другая ответственность); тесты, которым хватает `httptest` внутри процесса ([../cicd/integration-tests.md](../cicd/integration-tests.md)).

## Стек

```yaml
# Три сервиса: приложение, статика/фронт (здесь — эхо-сервер вместо него) и
# обратный прокси с внутренним TLS. Один вход, порты только на loopback.
services:
  backend:
    build: ./backend
    # healthcheck обязателен: без него `up --wait` возвращает управление в
    # момент старта процесса, а не готовности.
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:8080/healthz >/dev/null"]
      interval: 2s
      timeout: 2s
      retries: 10

  whoami:
    image: traefik/whoami:latest
    # Образ FROM scratch: внутри нет ни шелла, ни wget, ни curl — healthcheck
    # тут не выполним в принципе. Честный вариант — service_started, либо
    # образ, у которого есть чем проверить.
    # healthcheck: невозможен

  proxy:
    image: caddy:2-alpine
    depends_on:
      backend: {condition: service_healthy}
      whoami: {condition: service_started}
    # 127.0.0.1 в начале обязателен: без него порт публикуется на 0.0.0.0, и
    # «локальный» стек становится доступен всей сети.
    ports:
      - "127.0.0.1:8443:8443"
    volumes:
      - ./caddy:/etc/caddy:ro
      - caddy-data:/data      # внутренний CA и сертификаты: не пересоздавать каждый раз
    # Эндпоинт админки: `/` у админ-API не существует (wget падает на 404 →
    # контейнер unhealthy), /config/ отдаёт 200.
    healthcheck:
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:2019/config/ >/dev/null"]
      interval: 2s
      timeout: 3s
      retries: 10

volumes:
  caddy-data:
```

## Обратный прокси

```caddy
# Имя хоста в адресе сайта обязательно: `https://:8443` (без хоста) даёт
# handshake с alert "internal error" — внутреннему CA не на что выпускать
# сертификат. Рабочая форма: localhost:PORT.
localhost:8443 {
	tls internal

	# API: путь проксируется как есть, backend видит исходный Host и X-Forwarded-For.
	handle /api/* {
		reverse_proxy backend:8080
	}

	# Если приложению нужен путь без префикса — снимать явно:
	# handle /api/* {
	# 	uri strip_prefix /api
	# 	reverse_proxy backend:8080
	# }

	handle /whoami/* {
		uri strip_prefix /whoami
		reverse_proxy whoami:80
	}

	# Фронт. Вариант «прокси на dev-сервер» включается, когда vite поднят как
	# сервис: reverse_proxy vite:5173. Ниже — форма, которая работает без него.
	handle / {
		respond "spa-index"
	}

	encode zstd gzip
}
```

## Заглушка приложения

```go
// Dev-заглушка: здоровье, эхо заголовков и поток с паузой. Последний эндпоинт
// нужен не для демо, а для пробы «буферизуется ли путь».
package main

import (
	"fmt"
	"net/http"
	"time"
)

func main() {
	mux := http.NewServeMux()

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		fmt.Fprint(w, "ok")
	})

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "backend: %s %s proto=%s fwd=%q host=%q\n",
			r.Method, r.URL.Path, r.Proto, r.Header.Get("X-Forwarded-For"), r.Host)
	})

	// Куски каждые 400 мс. Интервал меньше секунды сознательно: при интервале
	// в 1 секунду не отличить «проходит» от «батчится по секунде».
	mux.HandleFunc("GET /api/fast", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("content-type", "text/plain; charset=utf-8")
		w.WriteHeader(http.StatusOK)
		for i := 1; i <= 5; i++ {
			fmt.Fprintf(w, "fast-%d\n", i)
			if f, ok := w.(http.Flusher); ok {
				f.Flush()
			}
			time.Sleep(400 * time.Millisecond)
		}
	})

	if err := http.ListenAndServe(":8080", mux); err != nil {
		fmt.Println("сервер:", err)
	}
}
```

```dockerfile
FROM golang:1.27-alpine AS build
WORKDIR /src
COPY main.go .
# Не /srv: в alpine это уже каталог, и COPY файла в него кладёт файл внутрь
# (/srv/main), а CMD ["/srv"] падает с «is a directory».
RUN CGO_ENABLED=0 go build -o /usr/local/bin/app main.go

FROM alpine:3.22
COPY --from=build /usr/local/bin/app /usr/local/bin/app
CMD ["app"]
```

## Подъём и пробы

```bash
# Поднять стек и проверить то, что обычно «работает у меня, но не в браузере».
set -euo pipefail

COMPOSE="${COMPOSE:-docker compose}"
PROJECT="${PROJECT:-localstack}"
URL="${URL:-https://localhost:8443}"

up() {
  # --build: compose не пересобирает образ после правки Dockerfile сам, и
  # старое изображение будет повторять уже исправленную ошибку.
  $COMPOSE -p "$PROJECT" up -d --build --wait
}

status() {
  $COMPOSE -p "$PROJECT" ps --format '{{.Service}} {{.State}} {{.Health}}'
}

# TLS: проверяем, что handshake проходит и сертификат выдал внутренний CA.
tls_probe() {
  local issuer
  issuer=$(curl -skv "$URL/api/fast" 2>&1 | sed -n 's/.*issuer: //p' | head -n1)
  [ -n "$issuer" ] || { echo "TLS не поднят: $URL" >&2; return 1; }
  echo "выдано: $issuer"
}

# Проба потока: когда пришёл каждый кусок. Это единственный способ отличить
# «ничего не приходит» от «приходит пачкой в конце».
stream_probe() {
  local path="${1:-/api/fast}" start now
  start=$(date +%s%N)
  curl -N -sk "$URL$path" | while IFS= read -r line; do
    [ -n "$line" ] || continue
    now=$(date +%s%N)
    printf '%dms %s\n' $(( (now - start) / 1000000 )) "$line"
  done
}

# Заголовок, который должен видеть upstream: без него приложение не узнает,
# что запрос был по HTTPS.
forwarded_probe() {
  curl -sk "$URL/whoami/" | grep -iE 'host:|forwarded|x-real-ip' || echo "проброс заголовков не найден"
}

down() {
  $COMPOSE -p "$PROJECT" down -v
}
```

## Что показали замеры

Стек поднимался локально, пробы — `curl` с отметками времени. Caddy 2.11.9, nginx 1-alpine для сравнения.

| Проба | Измерено | Вывод |
|---|---|---|
| `up -d --wait` | `up` выходит 0 только когда health'ы зелёные; без `healthcheck` у сервиса — « unhealthy/starting» навсегда | ждать можно только то, у чего есть проверка готовности |
| HTTPS на `https://:8443` (без имени) | handshake валится: `alert internal error` | у сайта обязан быть хост: `localhost:8443` |
| HTTPS на `localhost:8443` | `issuer: CN=Caddy Local Authority` | внутренний CA работает, браузеру нужен доверий корень или исключение |
| `X-Forwarded-*`, `Host` | upstream видит `Host: localhost:8443`, `X-Forwarded-For: 172.18.0.1`, `X-Forwarded-Proto: https` | Caddy сохраняет исходный Host и добавляет XFF: приложение определяет схему по заголовку, а не по `r.TLS` |
| Поток 400 мс через Caddy (SSE, `text/plain`, со `gzip` и с `flush_interval 5s`) | куски пришли на 19/419/819/1222/1622 мс во всех вариантах | Caddy пропускает flushed-ответы сразу; настраивать `flush_interval` для этого не нужно |
| То же через nginx 1-alpine (`proxy_http_version 1.1`, `proxy_buffering` по умолчанию) | те же 400 мс между кусками | «nginx буферизует любые потоки» — народная правда: на коротких кусках не воспроизводится. Почему рвётся в других конфигурациях, здесь не проверялось; проверено только то, что короткие flushed-куски проходят |
| Публикация порта `"8443:8443"` | `docker compose port` показал `0.0.0.0:8443` | без `127.0.0.1:` локальный стек слышен всей сетью; смена привязки требует пересоздания контейнера, `reload` не поможет |

## Ловушки

| Симптом | Причина | Что делать |
|---|---|---|
| Браузер не даёт микрофон/камеру | вне `localhost` нужен защищённый контекст | внутренний TLS, либо `chrome://flags` для временного исключения в своей разработке |
| `curl: (60)` / браузер ругается на сертификат | корень внутреннего CA не доверен | экспорт корня из `/data/caddy/pki` в доверенные хранилища, `skip_install_trust` + ручная установка |
| `exec: "/srv": is a directory` | в базовом образе `/srv` — каталог | бинарник в `/usr/local/bin` |
| Контейнер вечно `starting` | healthcheck нечем выполнить (scratch-образ) | `service_started` или образ, где есть чем проверить |
| Изменил Dockerfile — ошибка та же | compose переиспользует собранный образ | `up -d --build` |
| Порт «сменили», а он старый | привязка портов применяется при создании контейнера | `up -d --force-recreate` |
| 404 вместо статики | каталог смонтирован не туда, где лежит `root` | проверять путём внутри контейнера, а не снаружи |
| Бэкенд считает, что запрос был HTTP | `X-Forwarded-Proto` не смотрят | читать заголовок на прокси-границе, а не `r.TLS` |

## Related

- [../cicd/integration-tests.md](integration-tests.md) — тот же стек в CI: `-p` на прогон, съём томов, логи в артефакт
- [../cicd/docker.md](docker.md) — образы, healthcheck'и, многоступенчатая сборка
- [../react/snippets/vite.md](../react/snippets/vite.md) — dev-сервер и его собственный proxy: когда достаточно его
- [../llm/snippets/streaming.md](../llm/snippets/streaming.md) — поток ответа и прокси по пути
- [../go/snippets/websocket.md](../go/snippets/websocket.md) — долгое соединение через прокси и idle-таймауты
- [rules.md](rules.md) — правила раздела: секреты, привязки портов, читаемые падения
