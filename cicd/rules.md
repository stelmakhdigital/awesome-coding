---
id: cicd-rules
title: "CI/CD Rules (GitHub Actions, GitLab CI, Docker, Kubernetes)"
lang: cicd
min_version: null
category: rule-set
tags: [rules, guardrails, github-actions, gitlab-ci, docker, kubernetes, supply-chain]
status: stable
updated: 2026-11-24
---

# CI/CD Rules — обязательные правила

## Пайплайн

- ✅ Кэш зависимостей с ключом по lock-файлу (`hashFiles('**/package-lock.json')`,
  `go mod` кэш) — без кэша CI медленнее в разы и чаще падает на сети.
- ✅ `timeout-minutes` на job и `concurrency` с отменой устаревших прогонов в PR.
- ✅ Минимальные права: `permissions: contents: read` по умолчанию, повышение — точечно.
- ❌ `pull-requests: write` / `id-token: write` «на всякий случай» в каждом job.
- ✅ Деплой того же артефакта, что был собран и протестирован (build once, deploy many),
  а не пересборка на этапе deploy.
- ✅ Матрица версий языка (текущая + fallback из `AGENTS.md`), не «один образ на всё».
- ❌ `push`-событие в чужой PR с доступом к секретам (`pull_request_target` без
  ревью кода) — прямой путь к утечке токена.

## Секреты и supply chain

- ✅ Сторонние actions — по SHA (или свой форк), свои — по тегу major; `dependabot`/
  renovate на обновления тулчейна.
- ✅ Секреты — из secret store провайдера; в облако — короткий OIDC-токен вместо
  долгосрочных ключей ([secrets.md](secrets.md)).
- ❌ `echo "$TOKEN"`, `set -x` в месте, где в окружении есть секрет; секрет в имени
  тега, в кэше и в артефакте.
- ❌ `curl … | bash` и `RUN pip install` без закреплённой версии в Dockerfile.
- ✅ Проверка подписи/digest базового образа, если он из внешнего реестра.

## Docker

- ✅ Multi-stage: сборка отдельно, в финальный образ — только бинарь/артефакт.
- ✅ Базовый образ минимальный (`*-alpine`, `-slim`, distroless) и с закреплённой версией.
- ✅ `USER` non-root; файлы — с правами, а не `chmod 777`.
- ✅ `HEALTHCHECK` (или readiness-проба на стороне оркестратора).
- ❌ Секрет в `ENV`/`ARG` — остаётся в слое и в `docker history`.
- ❌ `latest` в production-манифестах: откат становится «угадай, что было раньше».

## Kubernetes

- ✅ `requests` и `limits` на каждый контейнер; без них воркер вытесняется или забивается.
- ✅ `readinessProbe` (пустить трафик) и `livenessProbe` (перезапустить) — разные пробы;
  readiness не должен зависеть от внешней системы, которую можно положить.
- ✅ Graceful shutdown: SIGTERM → доработать → выйти; `preStop`-задержка и
  `terminationGracePeriodSeconds` больше времени доработки
  ([graceful-shutdown.md](../go/snippets/graceful-shutdown.md)).
- ✅ `maxUnavailable`/`maxSurge` осмысленные, PDB для реплик > 1.
- ❌ Миграция схемы в startup-коде пода (гонка реплик); миграция — отдельный шаг пайплайна.
- ✅ Секреты — Secret + смонтированный файл/env; rotation описан, а не «пересоздать под».

## Релиз и откат

- ✅ У релиза есть версия и план отката; образы и миграции совместимы с предыдущей версией
  (expand → migrate → contract).
- ✅ Проверка «зелёный CI = деплоится», а не «зелёный CI = собралось».
- ❌ Ручные правки в проде как часть процесса.

## Related

- [secrets.md](secrets.md) — секреты и OIDC
- [matrix.md](matrix.md) — матричные сборки
- [k8s.md](k8s.md) — манифесты и паттерны
- [../shared/security.md](../shared/security.md) — общие принципы безопасности
