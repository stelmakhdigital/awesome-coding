---
id: py-idioms
title: "Python Idioms"
lang: python
min_version: "3.14"
category: idioms
tags: [idioms, style, dataclass, match, walrus, contextlib]
status: stable
updated: 2026-09-06
---

# Python Idioms — идиоматичный Python (3.14)

Код проверен на Python 3.14.7 (выполнен).

## Dataclass и DTO

```python
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Order:
    id: str
    total: int  # центы
    status: str = "new"


# copy через dataclasses.replace (frozen — иммутабелен).
import dataclasses

confirmed = dataclasses.replace(order := Order("42", 1000), status="confirmed")
print(order.status, confirmed.status)  # new confirmed
```

## Match (структурное сопоставление)

```python
def describe(shape: dict) -> str:
    match shape:
        case {"kind": "circle", "radius": r}:
            return f"circle r={r}"
        case {"kind": "rect", "width": w, "height": h}:
            return f"rect {w}x{h}"
        case _:
            return "unknown"


print(describe({"kind": "circle", "radius": 5}))  # circle r=5
```

## Walrus и генераторы

```python
# Walrus := — присвоение в выражении.
data = [1, 2, 3, 4, 5]
total = 0
for x in data:
    total += x
print(sum(1 for x in data if (y := x * 2) > 4))  # 3

# Генераторы: ленивые, O(1) память.
def chunks(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


print(list(chunks([1, 2, 3, 4, 5], 2)))  # [[1,2],[3,4],[5]]
```

## Context managers

```python
from contextlib import contextmanager, suppress


# Декоратор для контекстного менеджера.
@contextmanager
def tracked(label: str):
    print(f"start {label}")
    try:
        yield
    finally:
        print(f"end {label}")


with tracked("db"):
    pass

# suppress: «ожидаемая» ошибка без try/except.
with suppress(FileNotFoundError):
    open("no-such-file")
print("ok")
```

## Типизация (3.14)

```python
from typing import TypeAlias

# TypeAlias: именованные типы.
Status: TypeAlias = str | int


def check(v: Status) -> bool:
    return isinstance(v, (str, int))


# PEP 695: type-псевдонимы (3.12+).
type OrderId = str


def order_id(v: OrderId) -> OrderId:
    return v.strip()


print(check("a"), order_id(" 42 "))  # True 42
```

## Правила

1. ✅ `frozen=True, slots=True` для DTO (иммутабельность + память).
2. ✅ `match` — вместо цепочек `if/elif` по структуре.
3. ✅ `contextlib` — для переиспользуемых context managers.
4. ❌ Глобальное состояние — в dataclass/конфиг, не в модульных переменных.

## Related

- [rules.md](rules.md)
- [snippets/error-handling.md](snippets/error-handling.md)
