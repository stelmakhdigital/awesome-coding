---
id: cicd-secrets
title: "CI: секреты (GitHub Actions, OIDC, маскирование)"
lang: cicd
min_version: null
category: snippet
tags: [secrets, security, github-actions, oidc, masking, ci]
status: stable
updated: 2026-09-07
---

# Секреты в CI

**Когда использовать** — любой доступ CI к облакам, реестрам, БД, API: токены, ключи, сертификаты.
**Когда НЕ использовать** — публичные данные (это переменные окружения, не секреты).

## GitHub Actions

```yaml
name: deploy
on:
  push:
    branches: [main]

permissions:            # минимальные: только то, что нужно
  contents: read
  id-token: write       # для OIDC (короткоживущие облачные токены)

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: prod   # опционально: approval-гейт перед деплоем
    steps:
      - uses: actions/checkout@v4

      # Короткоживущий токен AWS (15 мин) вместо постоянного ключа.
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/ci-deploy
          aws-region: eu-central-1

      # Секрет — в env шага, не в аргументах/артефактах.
      - run: ./deploy.sh
        env:
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
```

## Правила

1. **Секрет — только из secret store** (`secrets.*`), никогда в `vars.*`, коде,
   артефактах, `build-args` Docker, логах.
2. **Короткоживущие токены вместо постоянных ключей**: OIDC → role assumption
   (AWS/GCP/Azure). Постоянный API-ключ в CI — технический долг.
3. **Минимальные привилегии**: `permissions:` на workflow/job; облачная роль —
   только нужные действия (deploy ≠ admin).
4. **Маскирование**: GitHub маскирует `secrets.*` в логах автоматически;
   свои секреты (из файла, из API) — `echo "::add-mask::${TOKEN}"`.
5. **Не печатайте окружение целиком** (`env | sort` в логах — классика утечки).
6. **`environment:` для прод-деплой** — approval и аудит «кто/когда/почему».
7. **Секрет в Docker-образ не попадает**: `--secret` (BuildKit) для build-time,
   env-инжект в рантайме — для run-time.
8. **Ротация**: секреты CI ротируются (90 дней); доступ к secret store —
   только owners + audit log.

## Pitfalls

- **`echo $TOKEN` «чтобы отладить»** — секрет в логах = секрет в истории CI
  (логи живут месяцами).
- **Секрет в `build-args`** — попадает в метаданные образа (`docker inspect`).
- **Один секрет на всё** (master-ключ) — утечка = полный компромисс; секреты
  по назначению (deploy, db, registry).
- **Self-hosted runner + секреты**: runner видит всё окружение — self-hosted
  только для доверенных репозиториев.
- **Секрет в fork/PR**: PR из внешних форков не получает `secrets.*`
  (pull_request из другого репо) — ожидаемое поведение, не «баг CI».

## Related

- [github-actions.md](github-actions.md)
- [gitlab-ci.md](gitlab-ci.md)
- [../shared/security.md](../shared/security.md)
