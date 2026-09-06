---
id: py-rules
title: "Python Rules"
lang: python
min_version: "3.14"
category: rule-set
tags: [rules, guardrails, style, typing, errors]
status: stable
updated: 2026-09-06
---

# Python Rules — обязательные правила

## Стиль и типы

- ✅ PEP 8 (ruff — линтер+форматтер).
- ✅ **Type hints — на всём публичном API** (функции, классы, модули).
- ✅ `from __future__ import annotations` не нужен (3.14: PEP 649/749 — ленивые аннотации).
- ✅ `X | None` вместо `Optional[X]`; `list[str]` вместо `List[str]`.
- ✅ `dataclass`/`@dataclass(frozen=True)` для DTO; `TypedDict` для dict-контрактов.
- ❌ Мутабельные дефолтные аргументы (`def f(x=[])`).

## Код

- ✅ `pathlib.Path` — не `os.path`.
- ✅ f-strings — не `%`/`.format`.
- ✅ `with` (context managers) для ресурсов (файлы, соединения, блокировки).
- ✅ `enumerate`/`zip` — не ручные индексы.
- ✅ Иммутабельность: `tuple`/`frozenset`/`frozen dataclass`, где уместно.
- ❌ Голый `except:` (ловит даже `KeyboardInterrupt`).

## Асинхронность

- ✅ `asyncio` + `async/await`; `asyncio.TaskGroup` (3.11+) для параллелизма.
- ✅ `asyncio.timeout` (3.11+) — таймауты.
- ❌ Блокирующие вызовы в async-коде (`time.sleep`, sync-HTTP) — `asyncio.to_thread` / async-библиотеки.

## Ошибки

- ✅ Кастомные исключения с кодами (`class OrderError(Exception): code = "ORDER_ERROR"`).
- ✅ `raise ... from err` — цепочка причин (context).
- ✅ `try/except` — на границах; `finally` — для cleanup.
- ✅ `contextlib` — для сложных context managers.

## Тесты

- ✅ pytest; фикстуры — для состояния; параметризация (`@pytest.mark.parametrize`) — для таблиц.
- ✅ `monkeypatch`/инъекция зависимостей — не глобальные моки.
- ❌ `time.sleep` в тестах.

## Related

- [idioms.md](idioms.md) — идиомы
- [decisions.md](decisions.md) — выбор библиотек
- [shared/error-handling.md](../shared/error-handling.md)
