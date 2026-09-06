---
id: py-web-server
title: "Python: web-сервер (FastAPI, Pydantic v2, DI, lifespan)"
lang: python
min_version: "3.11"
category: snippet
tags: [fastapi, web, http, server, pydantic, api]
status: stable
updated: 2026-09-07
---

# Web-сервер: FastAPI

**Когда использовать** — новый HTTP API на Python: async, валидация и OpenAPI из коробки.
**Когда НЕ использовать** — высоконагруженный/низкоуровневый: Litestar; простой скрипт-сервис: stdlib `http.server` не для продакшена — см. [decisions.md](../decisions.md).

## Код

```python
"""FastAPI: минимальный сервис (Pydantic v2, lifespan, DI)."""

from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field


class ItemStore:
    """Заместитель репозитория: в проде — БД, здесь — dict."""

    def __init__(self) -> None:
        self._items: dict[int, dict[str, object]] = {1: {"id": 1, "name": "Cup", "price_cents": 350}}
        self._next_id = 2

    def get(self, item_id: int) -> dict[str, object] | None:
        return self._items.get(item_id)

    def add(self, name: str, price_cents: int) -> dict[str, object]:
        item = {"id": self._next_id, "name": name, "price_cents": price_cents}
        self._items[self._next_id] = item
        self._next_id += 1
        return item


# Lifespan: старт/остановка ресурсов (БД, кэш) — не on_event (deprecated).
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.store = ItemStore()
    yield
    # здесь: закрытие соединений


app = FastAPI(title="Items API", lifespan=lifespan)


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price_cents: int = Field(ge=0)


class Item(BaseModel):
    id: int
    name: str
    price_cents: int


def get_store(request: Request) -> ItemStore:
    """DI: FastAPI резолвит Depends на каждый запрос; app — через request.app."""
    return request.app.state.store


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int, store: ItemStore = Depends(get_store)) -> Item:
    item = store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return Item.model_validate(item)


@app.post("/items", response_model=Item, status_code=201)
async def create_item(payload: ItemCreate, store: ItemStore = Depends(get_store)) -> Item:
    return Item.model_validate(store.add(payload.name, payload.price_cents))
```

Тест (pytest + TestClient — httpx под капотом):

```python
from fastapi.testclient import TestClient

from main import app  # noqa: F401  (модуль сервиса)


def test_crud() -> None:
    with TestClient(app) as client:
        assert client.get("/healthz").json() == {"status": "ok"}

        resp = client.post("/items", json={"name": "Mug", "price_cents": 500})
        assert resp.status_code == 201
        item = resp.json()

        assert client.get(f"/items/{item['id']}").json() == item
        assert client.get("/items/9999").status_code == 404

        # Валидация Pydantic — 422, не 500.
        assert client.post("/items", json={"name": "", "price_cents": -1}).status_code == 422
```

## Pitfalls

- **Не `app: FastAPI` в параметрах зависимостей** — приложение не инжектится; состояние — через `request.app.state`.
- **`async def` эндпоинт не должен блокировать**: блокирующий вызов (sync-БД, `time.sleep`) — в `def` (FastAPI уводит в threadpool) или в `asyncio.to_thread`.
- `response_model` — обязательный: без него в ответ уйдёт всё, что вы вернёте (включая приватные поля ORM).
- Ошибки валидации — автоматически `422` со структурированным телом; кастомные — `HTTPException`/`ExceptionMiddleware`, не «голые» `Exception`.
- CORS — `app.add_middleware(CORSMiddleware, allow_origins=[...])` с ячным списком, не `*` + credentials.
- Секреты — из env (см. [shared/configuration.md](../../shared/configuration.md)), не из `appsettings`/hardcode.
- OpenAPI генерируется автоматически (`/docs`) — ревьюите схему как контракт.

## Related

- [http-client.md](http-client.md)
- [json.md](json.md)
- [asyncio.md](asyncio.md)
- [shared/api-design.md](../../shared/api-design.md)
