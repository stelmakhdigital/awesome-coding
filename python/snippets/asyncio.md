---
id: py-asyncio
title: "Python: asyncio (TaskGroup, timeout, semaphore, отмена)"
lang: python
min_version: "3.11"
category: snippet
tags: [asyncio, async, concurrency, timeout, taskgroup, cancellation]
status: stable
updated: 2026-09-07
---

# asyncio

**Когда использовать** — I/O-параллелизм в Python: HTTP-клиенты, БД, очереди; один поток, тысячи задач.
**Когда НЕ использовать** — CPU-задачи (парсинг, вычисления): `concurrent.futures.ProcessPoolExecutor` или отдельный процесс; блокирующие вызовы — через `to_thread`.

## Код

```python
"""asyncio: TaskGroup, timeout, semaphore, отмена, to_thread."""

import asyncio
import logging

import httpx

log = logging.getLogger(__name__)


async def fetch_all(urls: list[str], *, limit: int = 8) -> list[str]:
    """Параллельный GET с ограничением параллелизма и таймаутом на задачу."""
    sem = asyncio.Semaphore(limit)
    results: list[str] = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:

        async def one(url: str) -> None:
            async with sem:  # не больше `limit` одновременных запросов
                async with asyncio.timeout(10):  # 3.11+: отмена по таймауту
                    resp = await client.get(url)
                    resp.raise_for_status()
                    results.append(resp.text)

        # TaskGroup (3.11+): все задачи завершатся; при первой ошибке
        # остальные отменяются, ошибка — ExceptionGroup.
        try:
            async with asyncio.TaskGroup() as tg:
                for url in urls:
                    tg.create_task(one(url))
        except* httpx.HTTPStatusError as eg:
            log.warning("some requests failed: %d", len(eg.exceptions))
            # Частичный успех: results уже содержит успешные ответы.
        return results


async def with_retry(coro_factory, *, attempts: int = 3, base: float = 0.5):
    """Ретрай с экспоненциальным backoff (0.5s, 1s, 2s)."""
    for i in range(attempts):
        try:
            return await coro_factory()
        except (httpx.TransportError, TimeoutError):
            if i == attempts - 1:
                raise
            await asyncio.sleep(base * 2**i)


def blocking_work() -> int:
    """Блокирующая работа (CPU/legacy-библиотека)."""
    import time

    time.sleep(1)
    return 42


async def run_blocking_in_thread() -> int:
    """Блокирующий вызов — в пуле потоков, не в event loop."""
    return await asyncio.to_thread(blocking_work)


async def main() -> None:
    urls = [f"https://httpbin.org/get?i={i}" for i in range(20)]
    texts = await fetch_all(urls)
    print(f"ok: {len(texts)}/{len(urls)}")

    value = await run_blocking_in_thread()
    print(value)

    # Отмена задачи: cancel + await, чтобы отмена завершилась.
    task = asyncio.create_task(asyncio.sleep(10))
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("task cancelled")


if __name__ == "__main__":
    asyncio.run(main())  # единственный вход в event loop
```

## Pitfalls

- **`asyncio.run()` — один раз, в `__main__`**: не вызывайте его внутри других async-функций и не создавайте второй loop.
- **Блокирующие вызовы** (`time.sleep`, `requests`, CPU-цикл) в event loop — останавливают все задачи: `to_thread` / `run_in_executor`.
- `asyncio.create_task` без `await` — задача может потеряться (не будет выполнена, ошибка проигнорирована). Держите ссылку или используйте `TaskGroup`.
- `asyncio.gather` без `return_exceptions=True` — первая ошибка убивает остальных **без** отмены (они продолжают висеть); `TaskGroup` отменяет корректно.
- `asyncio.timeout` (3.11+) предпочтительнее `wait_for`: не оборачивает результат, отменяет только тело.
- `CancelledError` — не «проглатывайте» его `except Exception` (с 3.8 он не наследуется от `Exception`, но ловля `BaseException` опасна).
- Тестирование: `asyncio.run` в каждом тесте или `pytest-asyncio`; event loop не переживает тесты.

## Alternatives

- `trio` — строгая структурированная конкурентность (если проект позволяет).
- `anyio` — абстракция над asyncio/trio (библиотеки, поддерживающие оба).

## Related

- [http-client.md](http-client.md)
- [error-handling.md](error-handling.md)
- [shared/concurrency.md](../../shared/concurrency.md)
