---
id: js-error-handling
title: Error handling: custom errors, timeout, global handlers
lang: javascript
min_version: "ES2024"
category: snippet
tags: [errors, async, node, timeout]
status: stable
updated: 2026-09-06
---

# Error handling

**Когда использовать** — Node.js/браузерный код с async-операциями.
**Когда НЕ использовать** — не применимо: это базовый слой.

## Код

```js
// 1. Кастомная ошибка: наследник Error с полями.
class HttpError extends Error {
  constructor(status, body) {
    super(`HTTP ${status}`);
    this.name = 'HttpError';
    this.status = status;
    this.body = body;
  }
}

// 2. Fetch с таймаутом (AbortController).
async function fetchWithTimeout(url, { timeout = 10_000, ...init } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(
    () => controller.abort(new DOMException('timeout', 'TimeoutError')),
    timeout,
  );
  try {
    const res = await fetch(url, { ...init, signal: controller.signal });
    if (!res.ok) {
      throw new HttpError(res.status, await res.text());
    }
    return res;
  } finally {
    clearTimeout(timer);
  }
}

// 3. Retry с экспоненциальным backoff.
async function withRetry(fn, { attempts = 3, baseDelay = 200 } = {}) {
  let lastErr;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      if (i < attempts - 1) {
        await new Promise((r) => setTimeout(r, baseDelay * 2 ** i));
      }
    }
  }
  throw lastErr;
}

// 4. Глобальные хендлеры (Node.js): не молчать, а завершаться.
process.on('unhandledRejection', (err) => {
  console.error('unhandledRejection:', err);
  process.exit(1);
});
process.on('uncaughtException', (err) => {
  console.error('uncaughtException:', err);
  process.exit(1);
});

// 5. Использование.
try {
  const res = await withRetry(() => fetchWithTimeout('https://api.example.com'));
  const data = await res.json();
} catch (err) {
  if (err instanceof HttpError) {
    console.error(`API error ${err.status}: ${err.body}`);
  } else {
    console.error('unexpected:', err);
  }
}
```

## Pitfalls

- `fetch` не бросает на 4xx/5xx — проверяйте `res.ok`.
- `clearTimeout` в `finally`, иначе timer держит процесс живым.
- Не используйте `try/catch` вокруг `Promise.all` для «одной из многих» — используйте `Promise.allSettled`.
- `process.exit(1)` в глобальных хендлерах — осознанный выбор: состояние после uncaughtException ненадёжно.

## Related

- [../typescript/snippets/http-client.md](../typescript/snippets/http-client.md)
