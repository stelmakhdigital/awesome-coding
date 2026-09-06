---
id: py-error-handling
title: "Python: Error handling (исключения, contextlib, ретраи)"
lang: python
min_version: "3.14"
category: snippet
tags: [errors, exceptions, contextlib, retry, cleanup]
status: stable
updated: 2026-09-06
---

# Error handling (Python)

**Когда использовать** — любая работа с ошибками.
**Когда НЕ использовать** — n/a: базовый сниппет.

Код проверен на Python 3.14.7 (выполнен).

## Иерархия исключений

```python
# Базовый класс домена + специфичные.
class OrderError(Exception):
    """Базовая ошибка домена Order."""

    code = "ORDER_ERROR"


class OrderNotFoundError(OrderError):
    code = "ORDER_NOT_FOUND"

    def __init__(self, order_id: str) -> None:
        super().__init__(f"order {order_id} not found")
        self.order_id = order_id


class OrderValidationError(OrderError):
    code = "ORDER_VALIDATION"


# Ожидаемые ошибки — не throw, а возвращаемое значение.
def find_order(order_id: str) -> dict | None:
    """None = «не найдено» (ожидание), исключение — только сбой."""
    ...
```

## Цепочки причин (raise from)

```python
# from — сохраняет причину (context), traceback показывает обе.
def create_order(payload: dict) -> dict:
    try:
        validate(payload)
    except ValueError as err:
        raise OrderValidationError(str(err)) from err
    # ...
```

## Cleanup: finally и contextlib

```python
import contextlib


# finally: гарантированный cleanup.
def process(path: str) -> int:
    f = open(path)
    try:
        return len(f.readlines())
    finally:
        f.close()


# contextlib: переиспользуемый менеджер (см. idioms).
@contextlib.contextmanager
def db_transaction(conn):
    conn.execute("BEGIN")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
```

## Ретраи (без библиотек)

```python
import asyncio


async def retry_async(fn, attempts: int = 3, base_ms: int = 200):
    """Ретрай с экспоненциальным backoff (только идемпотентные операции)."""
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return await fn()
        except (ConnectionError, TimeoutError) as err:
            last = err
            if i < attempts - 1:
                await asyncio.sleep(base_ms * 2**i / 1000)
    assert last is not None
    raise last
```

## Правила

1. ✅ **Ожидаемые** — `None`/`Result`; **непредвиденные** — исключения.
2. ✅ `raise ... from err` — не терять причину.
3. ❌ Голый `except:` (ловит `KeyboardInterrupt`/`SystemExit`).
4. ✅ `finally`/context manager — для cleanup, не «руками».
5. ✅ Ретрай — только временные ошибки (`ConnectionError`, `TimeoutError`).

## Related

- [shared/error-handling.md](../../shared/error-handling.md)
- [idioms.md](../idioms.md) — contextlib
