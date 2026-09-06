---
id: py-http-client
title: HTTP client (httpx, sync + async)
lang: python
min_version: "3.11"
category: snippet
tags: [http, httpx, async, client]
status: stable
updated: 2026-09-06
---

# HTTP client (httpx)

**Когда использовать** — HTTP-клиент в Python: `httpx` (sync и async, таймауты из коробки).
**Когда НЕ использовать** — нужен только sync и минимальные зависимости: `requests`.

## Код

```python
# pip install httpx
import httpx


class HttpClient:
    """Обёртка над httpx.Client: base_url, таймауты, raise_for_status."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout)

    def get(self, path: str, **kwargs: object) -> httpx.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, json: object | None = None, **kwargs: object) -> httpx.Response:
        return self._request("POST", path, json=json, **kwargs)

    def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        res = self._client.request(method, path, **kwargs)
        res.raise_for_status()  # бросает HTTPStatusError на 4xx/5xx
        return res

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


# Использование (sync): соединение переиспользуется.
with HttpClient("https://api.example.com") as client:
    res = client.get("/items")
    items: list[dict[str, object]] = res.json()


# Async-вариант.
async def fetch_items() -> list[dict[str, object]]:
    async with httpx.AsyncClient(base_url="https://api.example.com", timeout=10.0) as client:
        res = await client.get("/items")
        res.raise_for_status()
        return res.json()
```

## Pitfalls

- Всегда `raise_for_status()` — иначе 4xx/5xx выглядят как успех.
- Клиент закрывайте (`with`/`close()`): соединение утекает, event loop держит таймеры.
- `res.json()` бросает `json.JSONDecodeError` на не-JSON теле.
- Не создавайте `httpx.Client` на каждый запрос — теряется connection pooling.
- `timeout` — float (секунды) или `httpx.Timeout(connect=, read=, write=, pool=)`.

## Related

- [shared/api-design.md](../../shared/api-design.md) — контракты API (REST/gRPC/GraphQL)
