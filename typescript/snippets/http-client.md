---
id: ts-http-client
title: HTTP client (fetch + AbortController)
lang: typescript
min_version: "5.9"
category: snippet
tags: [http, fetch, async, timeout]
status: stable
updated: 2026-09-06
---

# HTTP client

**Когда использовать** — HTTP-клиент на `fetch` с таймаутом и типизацией ответов.
**Когда НЕ использовать** — нужен retry/interceptors/кеширование: `ky` или `ofetch` (см. decisions.md, когда появится).

## Код

```ts
class HttpError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: string,
  ) {
    super(`HTTP ${status}`);
    this.name = 'HttpError';
  }
}

class HttpClient {
  constructor(
    private readonly baseUrl: string,
    private readonly timeout = 10_000,
  ) {}

  get<T>(path: string, init?: RequestInit): Promise<T> {
    return this.request<T>(path, { ...init, method: 'GET' });
  }

  post<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
    return this.request<T>(path, {
      ...init,
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);
    try {
      // Слияние внешнего signal с таймаутом (ES2024: AbortSignal.any).
      const signal = init.signal
        ? AbortSignal.any([init.signal, controller.signal])
        : controller.signal;

      const res = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        signal,
        headers: { 'content-type': 'application/json', ...init.headers },
      });

      if (!res.ok) {
        throw new HttpError(res.status, await res.text());
      }
      if (res.status === 204) {
        return undefined as T;
      }
      return (await res.json()) as T;
    } finally {
      clearTimeout(timer);
    }
  }
}

// Использование.
interface Item {
  id: string;
  name: string;
}

async function main(): Promise<void> {
  const client = new HttpClient('https://api.example.com');
  const items = await client.get<Item[]>('/items');
  console.log(items.length);
}
```

## Pitfalls

- `fetch` **не** бросает ошибку на 4xx/5xx — проверяйте `res.ok`.
- Таймаут только через `AbortController`; `clearTimeout` — в `finally`.
- `res.json()` бросает на не-JSON теле — обрабатывайте.
- Не передавайте `signal` дважды (в `init` и через `AbortSignal.any`) — конфликт.

## Related

- [../javascript/snippets/error-handling.md](../javascript/snippets/error-handling.md) — общие async-идиомы JS
