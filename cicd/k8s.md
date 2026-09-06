---
id: cicd-k8s
title: "Kubernetes: манифесты и паттерны"
lang: cicd
min_version: null
category: snippet
tags: [kubernetes, k8s, deployment, probes, hpa, secrets]
status: stable
updated: 2026-09-06
---

# Kubernetes — манифесты и паттерны

**Когда использовать** — деплой в k8s-кластер.
**Когда НЕ использовать** — один сервис без масштабирования (VM/контейнер).

## Базовый Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  labels: { app: app }
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate: { maxSurge: 1, maxUnavailable: 0 } # без потери capacity
  selector:
    matchLabels: { app: app }
  template:
    metadata:
      labels: { app: app }
    spec:
      securityContext:
        runAsNonRoot: true
        seccompProfile: { type: RuntimeDefault }
      containers:
        - name: app
          image: ghcr.io/org/app:SHA # конкретный SHA, не latest
          ports: [{ containerPort: 8080 }]
          resources:
            requests: { cpu: 100m, memory: 128Mi } # requests = scheduling
            limits: { cpu: 500m, memory: 512Mi }   # limits = OOM-страховка
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef: { name: app-secrets, key: database-url }
          readinessProbe: # готов ли принимать трафик
            httpGet: { path: /ready, port: 8080 }
            periodSeconds: 5
          livenessProbe: # жив ли (рестарт при сбое)
            httpGet: { path: /healthz, port: 8080 }
            periodSeconds: 10
            failureThreshold: 3
          startupProbe: # для медленного старта (JVM и т.п.)
            httpGet: { path: /healthz, port: 8080 }
            failureThreshold: 30
            periodSeconds: 2
```

## Probes: разница

| Проба | Вопрос | При сбое |
|---|---|---|
| `readiness` | принимать трафик? | убрать из Service (без рестарта) |
| `liveness` | жив? | рестарт контейнера |
| `startup` | успел стартовать? | защита liveness для медленных стартов |

**Правило**: `/ready` — «я и зависимости готовы» (БД, кэш); `/healthz` — «процесс не повис». Не путать: liveness на БД-зависимости — каскадные рестарты.

## Паттерны

| Паттерн | Суть |
|---|---|
| **requests/limits** | requests — для планировщика; limits — только для «ядовитых» контейнеров (иначе эвictions) |
| **HPA** | автоскейлинг по CPU/RPS (custom metrics) |
| **PodDisruptionBudget** | мин. доступных реплик при drain-ноды |
| **Secrets** | `secretKeyRef`, не `env` с literal; в prod — external-secrets (Vault) |
| **ConfigMap** | не-секретная конфигурация |
| **Namespaces** | по окружению (dev/staging/prod) + по команде |
| **NetworkPolicy** | default-deny + явные allow (микро-сегментация) |
| **Blue/green** | два Deployment + переключение Service (мгновенный откат) |

## Правила

1. ✅ Образ — по SHA (репетивность), не `latest`.
2. ✅ `runAsNonRoot` + `seccompProfile` — базовая гигиена.
3. ✅ Все три пробы при медленном старте (startup + liveness + readiness).
4. ✅ PDB на прода-сервисах.
5. ✅ Лимиты на namespace (`LimitRange`, `ResourceQuota`).
6. ❌ `latest` в prod; `privileged: true` «для отладки».
7. ❌ Secrets в ConfigMap / в коде / в логах.
8. ✅ Откат: `kubectl rollout undo` — проверять на staging.

## Related

- [docker.md](docker.md) — образы
- [github-actions.md](github-actions.md) — деплой из CI
