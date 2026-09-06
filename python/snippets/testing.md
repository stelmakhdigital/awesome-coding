---
id: py-testing
title: "Python: Testing (pytest, параметризация, фикстуры)"
lang: python
min_version: "3.14"
category: snippet
tags: [testing, pytest, fixtures, parametrize, unit-tests]
status: stable
updated: 2026-09-06
---

# Testing (Python, pytest)

**Когда использовать** — unit-тесты Python-кода.
**Когда НЕ использовать** — «тесты» для проверки запуска (это smoke).

Код проверен на Python 3.14.7 (выполнен через pytest).

## Табличные тесты (parametrize)

```python
import pytest


def clamp(x: int, lo: int, hi: int) -> int:
    # lo/hi, а не min/max: параметры не должны затенять встроенные.
    return max(lo, min(x, hi))


@pytest.mark.parametrize(
    ("x", "lo", "hi", "expected"),
    [
        (5, 0, 10, 5),
        (-1, 0, 10, 0),
        (11, 0, 10, 10),
    ],
)
def test_clamp(x: int, lo: int, hi: int, expected: int) -> None:
    assert clamp(x, lo, hi) == expected
```

## Фикстуры и изоляция

```python
import pytest


class FakeRepo:
    """Фейк: детерминированные данные, без БД."""

    def __init__(self) -> None:
        self._orders: dict[str, dict] = {}

    def save(self, order: dict) -> None:
        self._orders[order["id"]] = order

    def get(self, order_id: str) -> dict | None:
        return self._orders.get(order_id)


@pytest.fixture
def repo() -> FakeRepo:
    return FakeRepo()


def test_save_and_get(repo: FakeRepo) -> None:
    repo.save({"id": "42", "total": 100})
    assert repo.get("42") == {"id": "42", "total": 100}
    assert repo.get("nope") is None
```

## Асинхронные тесты

```python
import asyncio

import pytest


async def fetch_total() -> int:
    await asyncio.sleep(0)
    return 100


@pytest.mark.asyncio  # pytest-asyncio
async def test_fetch_total() -> None:
    assert await fetch_total() == 100
```

## Правила

1. **Одна причина — один тест**; `parametrize` — для вариантов.
2. **Фикстуры** — для состояния; `yield`-фикстуры — с cleanup.
3. ✅ Фейки/стабы (интерфейсы), не «реальная БД в unit-тесте».
4. ❌ `time.sleep` — фиксированное время через инъекцию.
5. ✅ Тестируйте ошибки: `pytest.raises`, не только happy path.

## Related

- [shared/testing.md](../../shared/testing.md)
- [../typescript/snippets/testing.md](../../typescript/snippets/testing.md) — vitest
