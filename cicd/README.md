# CI/CD — GitHub Actions, GitLab CI, Docker, Kubernetes

Паттерны и лучшие практики для CI/CD и деплоя.
Примеры — рецензированы (YAML валиден), не прогонялись в живом кластере.

## Конвенции

- **CI обязан**: линт + тесты + сборка артефакта; деплой — только зелёный CI.
- **Секреты** — только в secret store провайдера, не в переменных по умолчанию.
- **Кэширование** — зависимости + артефакты сборки (без кэша CI в 3–10 раз медленнее).
- **Матрица** — версии языка/ОС, не «один образ на всё».
- **Idempotent-деплой**: повторный деплой того же артефакта — безопасен.

## Структура раздела

- [github-actions.md](github-actions.md) — паттерны GitHub Actions
- [gitlab-ci.md](gitlab-ci.md) — паттерны GitLab CI
- [docker.md](docker.md) — Dockerfile и docker compose
- [k8s.md](k8s.md) — Kubernetes: манифесты и паттерны
- [secrets.md](secrets.md) — секреты в CI (OIDC, маскирование)
- [matrix.md](matrix.md) — матричные сборки (версии, кэш, fail-fast)
