---
id: ddd-overview
title: DDD: когда уместен
lang: shared
min_version: "n/a"
category: concept
tags: [ddd, domain, architecture, over-engineering]
status: stable
updated: 2026-09-06
---

# DDD — когда уместен

**Когда уместен:**

- бизнес-логика — ядро продукта (банки, e-commerce, логистика, медицина);
- сложные инварианты, которые нельзя нарушать;
- долгоживущая система (5+ лет) с растущим доменом;
- эксперты по домену участвуют в проектировании.

**Когда НЕ уместен:**

- CRUD поверх БД (тонкая бизнес-логика) — уровень 0;
- прототипы, скрипты, внутренние инструменты;
- команда не знает домен (DDD без ubiquitous language — формальность);
- «DDD-lite»: переименованные папки без поведения — антипаттерн.

## Структура

- [tactical/](tactical/README.md) — составляющие: [entity](tactical/entity.md), [value object](tactical/value-object.md), [aggregate](tactical/aggregate.md), [domain service](tactical/domain-service.md), [domain event](tactical/domain-event.md), [repository](tactical/repository.md).
- [strategic/](strategic/README.md) — границы и язык: [bounded context](strategic/bounded-context.md), [ubiquitous language](strategic/ubiquitous-language.md), [context mapping](strategic/context-mapping.md).

## Золотые правила

1. **Поведение в модели** (entity/aggregate), а не в сервисах — иначе anemic domain model.
2. **Инварианты защищает корень агрегата** — внешние объекты не меняют состояние напрямую.
3. **Доменный слой не зависит от инфраструктуры** (см. [hexagonal](../patterns/hexagonal.md)).
4. **Repository — на агрегат, а не на таблицу** (см. [repository](tactical/repository.md)).
5. **События — в прошедшем времени** (`OrderConfirmed`, не `ConfirmOrder`).

## Related

- [../decisions.md — уровень DDD для проекта](../decisions.md)
- [go/patterns/repository.md — реализация repository на Go](../../go/patterns/repository.md)
