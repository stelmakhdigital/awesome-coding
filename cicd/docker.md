---
id: cicd-docker
title: "Docker: Dockerfile и compose (best practices)"
lang: cicd
min_version: null
category: snippet
tags: [docker, dockerfile, compose, multi-stage, layers]
status: stable
updated: 2026-09-06
---

# Docker — Dockerfile и compose

**Когда использовать** — контейнеризация приложений.
**Когда НЕ использовать** — «контейнеризация ради контейнеризации» (локальный скрипт).

## Dockerfile (multi-stage, Go-пример)

```dockerfile
# syntax=docker/dockerfile:1

# --- Сборка ---
FROM golang:1.27 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download          # отдельный слой: кэш зависимостей
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /out/app ./cmd/server

# --- Runtime ---
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/app /app
USER nonroot:nonroot         # не root
EXPOSE 8080
ENTRYPOINT ["/app"]
```

## Правила Dockerfile

1. **Multi-stage**: сборка и runtime — разные образы (runtime без тулчейна).
2. **Кэш слоёв**: `go.mod`/`package.json` — отдельным слоем ДО исходников.
3. **Non-root**: `USER`/distroless `nonroot` — не root в runtime.
4. **Минимальный базовый образ**: distroless/alpine/slim (меньше CVE, меньше размер).
5. **Одна команда на образ**: один процесс = один контейнер.
6. ❌ `latest` без SHA в CI (нерепетивность); в prod — SHA/версия.
7. ❌ Секреты в `ENV`/слоях (остаются в истории образа) — runtime injection.
8. ✅ `.dockerignore`: `.git`, тесты, node_modules (не тащить в контекст).
9. ✅ `HEALTHCHECK` (или k8s-пробы) — контейнер знает, что он здоров.
10. ❌ `curl | sh` в RUN без проверки суммы.

## docker compose (dev)

```yaml
services:
  app:
    build: .
    ports: ["8080:8080"]
    environment:
      DATABASE_URL: postgres://app:app@db:5432/app
    depends_on:
      db:
        condition: service_healthy   # не просто "started"
    healthcheck:
      test: ["CMD", "/app", "-health"]
      interval: 10s
      timeout: 3s
      retries: 3

  db:
    image: postgres:18
    environment:
      POSTGRES_PASSWORD: app
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
    volumes: [dbdata:/var/lib/postgresql/data]

volumes:
  dbdata:
```

## Правила compose

1. ✅ `depends_on` + `condition: service_healthy` (порядок по здоровью, не по старту).
2. ✅ Локальные секреты — в `.env` (в `.gitignore`), не в yml.
3. ✅ Вolumes для данных БД (переживают рестарт контейнера).
4. ✅ Compose — для dev; в prod — оркестрация (k8s).
5. ❌ `ports` на БД в dev-компаде «для удобства» (экспозиция).

## Related

- [github-actions.md](github-actions.md) — сборка в CI
- [k8s.md](k8s.md) — деплой
