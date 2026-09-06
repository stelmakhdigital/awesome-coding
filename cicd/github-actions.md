---
id: cicd-github-actions
title: "GitHub Actions: паттерны"
lang: cicd
min_version: null
category: snippet
tags: [cicd, github-actions, workflows, matrix, caching, secrets]
status: stable
updated: 2026-09-06
---

# GitHub Actions — паттерны

**Когда использовать** — CI/CD на GitHub.
**Когда НЕ использовать** — GitLab (см. [gitlab-ci.md](gitlab-ci.md)).

## Базовый workflow (Go-пример)

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true # новый push отменяет старый (экономия)

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        go: ["1.26", "1.27"] # матрица версий
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-go@v5
        with:
          go-version: ${{ matrix.go }}
          cache: true # кэш модулей

      - run: go build ./...
      - run: go test -race ./...

  docker:
    runs-on: ubuntu-latest
    needs: test # деплой/сборка — только после тестов
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:latest
            ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## Паттерны

| Паттерн | Суть | Пример |
|---|---|---|
| **concurrency** | отмена устаревших запусков | `concurrency.group` + `cancel-in-progress` |
| **матрица** | версии языка/ОС | `strategy.matrix` |
| **needs** | порядок джоб | `needs: [test, lint]` |
| **if** | условия | `if: github.ref == 'refs/heads/main'` |
| **кэш** | зависимости/артефакты | `actions/cache`, `cache: true` в setup-* |
| **reusable workflow** | общий пайплайн | `uses: org/repo/.github/workflows/x.yml@v1` |
| **composite action** | переиспользуемые шаги | `actions/` в репо |
| **environments** | защита деплоя | `environment: production` + reviewers |
| **secrets** | только secret store | `${{ secrets.X }}`, не в `env:` по умолчанию |
| **артефакты** | между джобами | `actions/upload-artifact` / `download` |

## Правила

1. ✅ `pull_request` + `push: main` — покрытие обоих триггеров.
2. ✅ SHA-теги для образов, не только `latest`.
3. ✅ `cache` для зависимостей (Go modules, npm, pip).
4. ✅ `timeout-minutes` на джобах (страховка от зависаний).
5. ✅ Permissions — минимальные: `permissions: { contents: read }` по умолчанию.
6. ❌ Секреты в `env:` на уровне workflow (видны в логах при отладке).
7. ❌ `continue-on-error: true` «чтобы не падало».
8. ✅ Тесты безопасности: `gitleaks`/`trufflehog` (секреты в истории), `govulncheck`/`npm audit`.

## Related

- [gitlab-ci.md](gitlab-ci.md) — GitLab
- [docker.md](docker.md) — сборка образов
