---
id: ts-testing
title: "TypeScript: Testing (vitest, table-driven, async)"
lang: typescript
min_version: "7.0"
category: snippet
tags: [testing, vitest, unit-tests, async, mocking]
status: stable
updated: 2026-09-06
---

# Testing (TypeScript, vitest)

**Когда использовать** — unit-тесты в TS-проекте.
**Когда НЕ использовать** — «тесты» для проверки, что код запускается (это smoke, не тест).

Код проверен на tsc 7.0.2 (`strict: true`).

## Табличные тесты

```ts
import { describe, expect, it } from "vitest";

function clamp(x: number, min: number, max: number): number {
  return Math.min(Math.max(x, min), max);
}

const cases = [
  { x: 5, min: 0, max: 10, expected: 5 },
  { x: -1, min: 0, max: 10, expected: 0 },
  { x: 11, min: 0, max: 10, expected: 10 },
] as const;

describe("clamp", () => {
  for (const { x, min, max, expected } of cases) {
    it(`clamp(${x}, ${min}, ${max}) = ${expected}`, () => {
      expect(clamp(x, min, max)).toBe(expected);
    });
  }
});
```

## Асинхронные тесты и моки

```ts
import { describe, expect, it, vi } from "vitest";

// Мокируем зависимость.
const fetchMock = vi.fn();

describe("fetchOrder", () => {
  it("возвращает заказ при 200", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "42", total: 100 }),
    });

    const order = await fetchOrder("42", { fetch: fetchMock });
    expect(order.id).toBe("42");
  });

  it("бросает HttpError при 404", async () => {
    fetchMock.mockResolvedValueOnce({ ok: false, status: 404 });
    await expect(fetchOrder("nope", { fetch: fetchMock })).rejects.toMatchObject({
      code: "HTTP_ERROR",
      status: 404,
    });
  });
});

// Тестируемая функция: fetch — инъекция (не глобальный).
export class HttpError extends Error {
  constructor(
    readonly code: string,
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function fetchOrder(
  id: string,
  deps: { fetch: typeof fetch } = { fetch: globalThis.fetch },
): Promise<{ id: string; total: number }> {
  const res = await deps.fetch(`/orders/${id}`);
  if (!res.ok) {
    throw new HttpError("HTTP_ERROR", res.status, `GET /orders/${id}`);
  }
  return (await res.json()) as { id: string; total: number };
}
```

## Правила

1. **Одна причина — один тест**; таблица — для вариантов одного поведения.
2. **Инъекция зависимостей** (fetch, время, БД) — не мокируйте глобальные.
3. **`vi.fn()` + `mockResolvedValueOnce`** — детерминированная сеть.
4. ❌ `setTimeout`/`sleep` в тестах — фиксированное время через инъекцию.
5. ✅ Тестируйте ошибки: `rejects.toMatchObject`, не только happy path.

## Related

- [shared/testing.md](../../shared/testing.md)
- [javascript/snippets/testing.md](../../javascript/snippets/testing.md) — node:test
