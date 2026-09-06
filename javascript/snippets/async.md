---
id: js-async
title: "JavaScript: async (таймауты, ретраи, лимит параллелизма)"
lang: javascript
min_version: "ES2025"
category: snippet
tags: [async, timeout, retry, abort, concurrency, promise]
status: stable
updated: 2026-09-06
---

# Async (JavaScript)

**Когда использовать** — внешние вызовы (HTTP, БД), параллельная работа.
**Когда НЕ использовать** — CPU-задачи (worker_threads).

Код проверен на node v22.23.2 (выполнен).

## Таймаут и отмена

```js
// Таймаут: гонка промиса и таймера.
export function withTimeout(p, ms, label = "operation") {
  return new Promise((resolve, reject) => {
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
export async function fetchJson(url, { timeoutMs = 10_000, signal } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new Error("timeout")), timeoutMs);
  const outer = signal; // константа: сужение живёт в колбэке
  outer?.addEventListener("abort", () => controller.abort(outer.reason), { once: true });
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${url}`);
    }
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}
```

## Ретрай с backoff

```js
// Только для идемпотентных операций (GET).
export async function retry(fn, { attempts = 3, baseMs = 200, signal } = {}) {
  let lastErr;
  for (let i = 0; i < attempts; i++) {
    if (signal?.aborted) throw signal.reason ?? new Error("aborted");
    try {
      return await fn(signal);
    } catch (e) {
      lastErr = e;
      if (i < attempts - 1) {
        await sleep(baseMs * 2 ** i, signal); // 200, 400, 800 мс
      }
    }
  }
  throw lastErr;
}

export function sleep(ms, signal) {
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

```js
// mapLimit: не больше N одновременных вызовов.
export async function mapLimit(items, limit, fn) {
  const results = new Array(items.length);
  let next = 0;

  async function worker() {
    while (true) {
      const i = next++;
      if (i >= items.length) return;
      results[i] = await fn(items[i]);
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
- [error-handling.md](error-handling.md) — глобальные хендлеры
