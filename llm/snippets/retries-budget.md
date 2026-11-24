---
id: llm-retries-budget
title: "LLM: ретраи, бюджет и кэш вызовов (Python)"
lang: llm
min_version: "3.11"
category: snippet
tags: [llm, retry, budget, caching, httpx, python]
status: stable
updated: 2026-11-24
---

# Ретраи, бюджет и кэш (Python)

**Когда использовать** — массовая обработка (классификация, извлечение, разметка),
где важны и цена, и переживаемость сбоев провайдера.
**Когда НЕ использовать** — интерактивный UI с ответами по одному запросу: там
кэш по хешу входа почти не попадает, а стриминг устроен иначе
([../decisions.md](../decisions.md)).

## Код

```python
"""Вызов chat-completions-совместимого API: ретраи, бюджет, кэш.

Бюджет считается по usage ответа; кэш — по (модель, версия промпта, хеш входа),
чтобы повторный запрос не стоил денег и не зависел от того, что модель
«передумала».
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

# Повторяем только на «временно»: 4xx (кроме 408/409/429) — это битый запрос.
RETRY_STATUS = frozenset({408, 409, 429, 500, 502, 503, 504})


class BudgetExceeded(RuntimeError):
    """Остаток бюджета меньше прогнозируемой стоимости запроса."""


class SchemaError(ValueError):
    """Ответ не разбирается по ожидаемой структуре. Ретрай не помогает."""


@dataclass(frozen=True)
class Price:
    in_per_1m: float
    out_per_1m: float


def _usage_cost(price: Price, usage: dict[str, int]) -> float:
    return (usage.get("prompt_tokens", 0) * price.in_per_1m
            + usage.get("completion_tokens", 0) * price.out_per_1m) / 1_000_000


def _wait(resp: httpx.Response | None, fallback: float) -> float:
    """Retry-After важнее нашего backoff, но не длиннее разумного ожидания."""
    if resp is not None and (raw := resp.headers.get("retry-after")):
        try:
            return min(float(raw), 30.0)
        except ValueError:
            pass
    return min(fallback, 30.0)


@dataclass
class LLMClient:
    base_url: str
    api_key: str
    model: str
    price: Price
    budget_usd: float
    timeout: float = 60.0
    cache_ttl: float = 3600.0
    cache: dict[str, tuple[float, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._http = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"authorization": f"Bearer {self.api_key}"},
        )

    def close(self) -> None:
        self._http.close()

    @staticmethod
    def cache_key(model: str, prompt_version: str, messages: list[dict[str, str]]) -> str:
        h = hashlib.sha256()
        h.update(model.encode())
        h.update(prompt_version.encode())
        for m in messages:
            h.update(m["role"].encode())
            h.update(m["content"].encode())
        return h.hexdigest()

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        prompt_version: str = "v1",
        max_tokens: int = 512,
        attempts: int = 4,
        required_fields: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        key = self.cache_key(self.model, prompt_version, messages)
        hit = self.cache.get(key)
        if hit and hit[0] > time.monotonic():
            return json.loads(hit[1])

        # Оценка до отправки: хуже случая нет, платим по максимуму ответа.
        projected = (sum(len(m["content"]) for m in messages) / 4 * self.price.in_per_1m
                     + max_tokens * self.price.out_per_1m) / 1_000_000
        if self.budget_usd < projected:
            raise BudgetExceeded(f"остаток {self.budget_usd:.4f} < {projected:.4f}")

        delay = 0.5
        last_error: Exception | None = None
        for _ in range(attempts):
            resp = None
            try:
                resp = self._http.post(
                    "/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                    },
                )
            except httpx.TransportError as exc:      # сеть/таймаут — временно
                last_error = exc
            else:
                if resp.status_code in RETRY_STATUS:
                    last_error = RuntimeError(f"llm: http {resp.status_code}")
                else:
                    resp.raise_for_status()
                    return self._finish(resp, key, required_fields)
            time.sleep(_wait(resp, delay + random.random() * delay))
            delay *= 2

        raise RuntimeError(f"llm: {attempts} попыток: {last_error}")

    def _finish(self, resp: httpx.Response, key: str,
                required_fields: tuple[str, ...]) -> dict[str, Any]:
        data = resp.json()
        if error := data.get("error"):
            raise SchemaError(f"llm: api: {error}")
        choices = data.get("choices") or []
        if not choices:
            raise SchemaError("llm: пустой ответ (no choices)")

        usage = data.get("usage") or {}
        self.budget_usd -= _usage_cost(self.price, usage)

        content = choices[0]["message"]["content"]
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:          # не по схеме — не ретраим
            raise SchemaError(f"llm: ответ не JSON: {content[:200]!r}") from exc

        # Проверяем структуру, а не «похожесть на правду».
        if not isinstance(parsed, dict):
            raise SchemaError("llm: ожидался объект")
        missing = [f for f in required_fields if f not in parsed]
        if missing:
            raise SchemaError(f"llm: нет полей {missing}")

        self.cache[key] = (time.monotonic() + self.cache_ttl, json.dumps(parsed))
        return parsed
```

## Pitfalls

- `raise_for_status()` до проверки `RETRY_STATUS`: тогда 429 превращается в
  исключение и ретраев вы не увидите.
- Кэш без TTL и без учёта версии промпта в ключе: после правки промпта половина
  ответов приходит из кэша, и «улучшение» не находится.
- Бюджет, списываемый *до* ответа по оценке: при отказе провайдера вы списали деньги
  за несостоявшийся запрос. Списываем по `usage` после.
- `required_fields` проверяет наличие поля, а не его смысл; смысловые проверки —
  в [../evals.md](../evals.md).
- Один `httpx.Client` на потоки: он потокобезопасен, но общий таймаут и общий пул
  соединений — для массовой обработки заведите ограничение параллелизма
  (`anyio.Semaphore` или `threading.BoundedSemaphore`).

## Related

- [../rules.md](../rules.md) — что обязано быть в вызове
- [structured-output.md](structured-output.md) — тот же слой на Go
- [../../python/snippets/http-client.md](../../python/snippets/http-client.md) — httpx в репо
- [../../database/snippets/redis.md](../../database/snippets/redis.md) — кэш вне процесса
