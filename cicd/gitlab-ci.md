---
id: cicd-gitlab-ci
title: "GitLab CI: паттерны"
lang: cicd
min_version: null
category: snippet
tags: [cicd, gitlab-ci, stages, caching, artifacts]
status: stable
updated: 2026-09-06
---

# GitLab CI — паттерны

**Когда использовать** — CI/CD на GitLab.
**Когда НЕ использовать** — GitHub (см. [github-actions.md](github-actions.md)).

## Базовый .gitlab-ci.yml

```yaml
stages: [test, build, deploy]

default:
  image: golang:1.27
  cache:
    key:
      files: [go.sum] # кэш по go.sum
    paths: [/.cache/go-build, /root/go/pkg/mod]
  variables:
    GOFLAGS: "-buildvcs=false"

test:
  script:
    - go build ./...
    - go test -race ./...

build:
  stage: build
  image: docker:27
  services: [docker:27-dind]
  variables:
    DOCKER_HOST: unix:///var/run/docker.sock
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

deploy:
  stage: deploy
  image: bitnami/kubectl
  script:
    - kubectl set image deployment/app app=$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  environment:
    name: production
  when: manual # ручной триггер для прода
```

## Паттерны

| Паттерн | Суть | Пример |
|---|---|---|
| **stages** | порядок: test → build → deploy | `stages:` |
| **rules** | условия запуска (тоньше `only/except`) | `rules: - if:` |
| **cache** | зависимости по ключу | `cache.key.files` |
| **artifacts** | между джобами | `artifacts: paths/expire_in` |
| **include** | общие шаблоны | `include: - template: ...` / свой yml |
| **needs** | точные зависимости (параллельно) | `needs: [test]` |
| **environment** | среды + rollback | `environment: name` |
| **manual** | ручной деплой | `when: manual` |
| **retry** | повтор при сбое | `retry: 2` |

## Правила

1. ✅ `default:` — общий image/cache/variables (DRY).
2. ✅ Кэш — по `go.sum`/`package-lock.json` (ключ), не «весь репо».
3. ✅ `rules` вместо `only/except` (современный синтаксис).
4. ✅ Деплой прода — `when: manual` + `environment` (аудит, rollback).
5. ✅ Артефакты — с `expire_in` (не копить).
6. ❌ Секреты в `variables` без `masked`/`protected`.
7. ❌ Один mega-джоб на всё (stage-разделение = параллельность).
8. ✅ `needs` для независимых джоб (быстрее, чем stage-барьер).

## Related

- [github-actions.md](github-actions.md) — GitHub
- [k8s.md](k8s.md) — деплой в k8s
