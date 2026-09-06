---
id: py-json
title: "Python: JSON (pydantic, dataclasses, валидация)"
lang: python
min_version: "3.14"
category: snippet
tags: [json, pydantic, dataclass, validation, api]
status: stable
updated: 2026-09-06
---

# JSON (Python)

**Когда использовать** — парсинг/сериализация JSON с границ (API, env, файлы).
**Когда НЕ использовать** — внутренний код с уже валидными данными.

Код проверен на Python 3.14.7 (выполнен).

## Stdlib: json + dataclass

```python
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class Order:
    id: str
    total: int  # центы
    status: str = "new"


# Сериализация: dataclass -> dict -> JSON.
def serialize(order: Order) -> str:
    return json.dumps(asdict(order))


# Парсинг: JSON -> dict -> валидация -> dataclass.
def parse(raw: str) -> Order:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("invalid order: not an object")
    order_id = data.get("id")
    total = data.get("total")
    if not isinstance(order_id, str) or not order_id:
        raise ValueError("invalid order: id")
    if not isinstance(total, int) or total < 0:
        raise ValueError("invalid order: total")
    status = data.get("status", "new")
    if status not in {"new", "confirmed", "shipped"}:
        raise ValueError(f"invalid order: status={status!r}")
    return Order(id=order_id, total=total, status=status)


o = parse(serialize(Order("42", 100)))
assert o.id == "42"
```

## Pydantic v2 (когда нужна схема)

```python
# pip install pydantic
from pydantic import BaseModel, Field, ValidationError


class OrderModel(BaseModel):
    id: str
    total: int = Field(ge=0)
    status: str = "new"

    model_config = {"frozen": True}  # иммутабельность


def parse_strict(raw: str) -> OrderModel:
    try:
        return OrderModel.model_validate_json(raw)
    except ValidationError as err:
        details = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in err.errors())
        raise ValueError(f"invalid order: {details}") from err


m = parse_strict('{"id": "42", "total": 100}')
assert m.total == 100
```

## Правила

1. ✅ **Валидация на границе**: `json.loads` → проверка типов → объект.
2. ✅ Pydantic — когда схема переиспользуется (API, конфиг); dataclass — для простых DTO.
3. ❌ `json.loads` «и поехали» без проверки (внешние данные — враг).
4. ✅ `frozen=True, slots=True` для DTO.
5. ✅ `raise ... from err` в обёртках ValidationError.

## Related

- [shared/api-design.md](../../shared/api-design.md)
- [../typescript/snippets/json.md](../../typescript/snippets/json.md) — zod
