---
id: bash-decisions
title: "Bash Decisions (bash vs python, инструменты)"
lang: bash
min_version: "5.3"
category: decisions
tags: [decisions, scripting, python, tooling, choices]
status: stable
updated: 2026-09-06
---

# Bash — таблицы решений

## Bash или другой язык?

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Оркестрация команд (CI, деплой) | **Bash** | Make, Python | glue-код |
| Обработка текста (сложная) | **Python** | awk/sed | логики > 50 строк |
| JSON/YAML-парсинг | **Python/jq** | — | bash не парсит форматы |
| Параллельная обработка файлов | bash + `xargs -P` | GNU Parallel | — |
| Интерактивные утилиты | Python/Go | bash | UX |

**Правило**: bash — для «запустить команды и склеить результат»; как только нужна логика
(циклы по данным, форматы, ошибки) — Python.

## Инструменты

| Задача | Рекомендация | Альтернатива |
|---|---|---|
| Линтер | **shellcheck** | — |
| Форматтер | shfmt | — |
| JSON | **jq** | python -c |
| HTTP | **curl** | wget |
| Параллельность | `xargs -P` | GNU Parallel |
| Тесты | bats-core | — |
| CI | GitHub Actions / GitLab CI | — |

## Bash-версии

| Задача | Рекомендация | Альтернатива |
|---|---|---|
| Новый скрипт | **bash 5.x** (`#!/usr/bin/env bash`) | — |
| macOS (системный 3.2) | brew bash / `env bash` | zsh |
| Портативность (CI-контейнеры) | bash 5 (debian/ubuntu) | sh (POSIX) |

## Related

- [rules.md](rules.md)
- [../python/decisions.md](../python/decisions.md)
