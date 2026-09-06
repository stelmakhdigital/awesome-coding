---
id: ts-async
title: "TypeScript: async (таймауты, ретраи, лимит параллелизма)"
lang: typescript
min_version: "7.0"
category: snippet
tags: [async, timeout, retry, abort, concurrency, promise]
status: stable
updated: 2026-09-06
---

# Async (TypeScript)

**Когда использовать** — внешние вызовы (HTTP, БД, очереди), параллельная работа.
**Когда НЕ использовать** — CPU-задачи (Node single-threaded: worker_threads).

Код проверен на tsc 7.0.2 (`strict: true`).

## Таймаут и отмена

```ts
// Таймаут: гонка промиса и таймера.
export function withTimeout<T>(
  p: Promise<T>,
  ms: number,
  label = "operation",
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`${label}: timeout ${ms}ms`)), ms);
    p.then(
      (v) => {
        clearTimeout(timer);
        resolve(v);
      },
      (e) => {
        clearTimeout(timer);
        reject(e);
      },
    );
  });
}

// Отмена: AbortController (сквозной signal).
export async function fetchJson<T>(
  url: string,
  opts: { timeoutMs?: number; signal?: AbortSignal } = {},
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(
    () => controller.abort(new Error("timeout")),
    opts.timeoutMs ?? 10_000,
  );
  // Внешний signal пробрасываем внутрь (константа: сужение живёт в колбэке).
  const outer = opts.signal;
  outer?.addEventListener("abort", () => controller.abort(outer.reason), { once: true });
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${url}`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}
```

## Ретрай с backoff

```ts
// Только для идемпотентных операций (GET).
export async function retry<T>(
  fn: (signal: AbortSignal) => Promise<T>,
  opts: { attempts?: number; baseMs?: number; signal?: AbortSignal } = {},
): Promise<T> {
  const { attempts = 3, baseMs = 200, signal } = opts;
  let lastErr: unknown;
  for (let i = 0; i < attempts; i++) {
    if (signal?.aborted) throw signal.reason ?? new Error("aborted");
    try {
      return await fn(signal ?? new AbortController().signal);
    } catch (e) {
      lastErr = e;
      if (i < attempts - 1) {
        await sleep(baseMs * 2 ** i, signal); // 200, 400, 800 мс
      }
    }
  }
  throw lastErr;
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(signal.reason ?? new Error("aborted"));
      },
      { once: true },
    );
  });
}
```

## Лимит параллелизма

```ts
// mapLimit: не больше N одновременных вызовов.
export async function mapLimit<T, R>(
  items: readonly T[],
  limit: number,
  fn: (item: T) => Promise<R>,
): Promise<R[]> {
  const results = new Array<R>(items.length);
  let next = 0;

  async function worker(): Promise<void> {
    while (true) {
      const i = next++;
      if (i >= items.length) {
        return;
      }
      const item = items[i];
      if (item === undefined) {
        return;
      }
      results[i] = await fn(item);
    }
  }

  const workers = Array.from({ length: Math.min(limit, items.length) }, worker);
  await Promise.all(workers);
  return results;
}
```

## Правила

1. **Таймаут — всегда** на внешних вызовах.
2. **AbortController — сквозной**: один signal на запрос, пробрасывается вниз.
3. **Ретрай — только идемпотентное** + экспоненциальный backoff.
4. ✅ `Promise.all` — независимые; `mapLimit` — с лимитом; `for..of` + await — зависимые.
5. ❌ `Promise.all` на 1000 URL без лимита (DoS себе).

## Related

- [shared/concurrency.md](../../shared/concurrency.md)
- [http-client.md](http-client.md) — fetch + AbortController
