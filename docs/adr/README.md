# ADR — архитектурные решения репозитория

Одно решение — один файл: `NNNN-short-title.md`. Формат: **Context → Decision → Consequences**
(подробности — [shared/documentation.md](../../shared/documentation.md)).

Статусы: `proposed → accepted → superseded by NNNN / deprecated`.
ADR не удаляют: ошибочное решение помечают `superseded`, новое решение — новым номером.

| # | Решение | Статус |
|---|---|---|
| [0001](0001-agent-first-design.md) | Agent-first дизайн: структура под чтение LLM-агентом | accepted |
| [0002](0002-pinned-versions.md) | Закреплённые версии технологий с fallback | accepted |
| [0003](0003-go-no-orm.md) | Без ORM в Go: database/sql + pgx / sqlc | accepted |
| [0004](0004-no-site-no-embeddings.md) | Ни сайта, ни векторного поиска: файлы и каталог — единственный доступ | accepted |
| [0005](0005-reviewed-is-ceiling-without-runner.md) | `reviewed` — потолок для разделов без тулчейна в CI | accepted |
| [0006](0006-tool-writes-metadata.md) | Метаданные выставляет прогон, а не автор | accepted |
