# CI/CD — GitHub Actions, GitLab CI, Docker, Kubernetes

Паттерны и лучшие практики для CI/CD и деплоя.
Примеры — рецензированы (YAML валиден), не прогонялись в живом кластере.

## Правила

Обязательные guardrails — в [rules.md](rules.md) (пайплайн, секреты и supply chain,
Docker, Kubernetes, релиз и откат). Здесь они не дублируются.

## Структура раздела

- [rules.md](rules.md) — обязательные правила (✅/❌)
- [github-actions.md](github-actions.md) — паттерны GitHub Actions
- [gitlab-ci.md](gitlab-ci.md) — паттерны GitLab CI
- [docker.md](docker.md) — Dockerfile и docker compose
- [k8s.md](k8s.md) — Kubernetes: манифесты и паттерны
- [secrets.md](secrets.md) — секреты в CI (OIDC, маскирование)
- [matrix.md](matrix.md) — матричные сборки (версии, кэш, fail-fast)
