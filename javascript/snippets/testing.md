---
id: js-testing
title: "JavaScript: Testing (node:test, stdlib)"
lang: javascript
min_version: "ES2025"
category: snippet
tags: [testing, node-test, unit-tests, mocking, stdlib]
status: stable
updated: 2026-09-06
---

# Testing (JavaScript, node:test)

**Когда использовать** — unit-тесты Node-кода без внешних зависимостей.
**Когда НЕ использовать** — TS-проекты (vitest), E2E (Playwright).

Код проверен на node v22.23.2 (выполнен).

## Табличные тесты

```js
import { describe, test } from "node:test";
import assert from "node:assert/strict";

function clamp(x, min, max) {
  return Math.min(Math.max(x, min), max);
}

const cases = [
  { x: 5, min: 0, max: 10, expected: 5 },
  { x: -1, min: 0, max: 10, expected: 0 },
  { x: 11, min: 0, max: 10, expected: 10 },
];

describe("clamp", () => {
  for (const { x, min, max, expected } of cases) {
    test(`clamp(${x}, ${min}, ${max}) = ${expected}`, () => {
      assert.equal(clamp(x, min, max), expected);
    });
  }
});
```

## Асинхронные тесты и моки

```js
import { describe, test, mock } from "node:test";
import assert from "node:assert/strict";

// Моки: node:test/mock (stdlib).
function makeFetcher(fetchImpl) {
  return async function fetchOrder(id) {
    const res = await fetchImpl(`/orders/${id}`);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: GET /orders/${id}`);
    }
    return res.json();
  };
}

describe("fetchOrder", () => {
  test("возвращает заказ при 200", async () => {
    const fetchMock = mock.fn(async () => ({
      ok: true,
      json: async () => ({ id: "42", total: 100 }),
    }));
    const order = await makeFetcher(fetchMock)("42");
    assert.equal(order.id, "42");
    assert.equal(fetchMock.mock.callCount(), 1);
  });

  test("бросает при 404", async () => {
    const fetchMock = mock.fn(async () => ({ ok: false, status: 404 }));
    await assert.rejects(
      makeFetcher(fetchMock)("nope"),
      /HTTP 404/,
    );
  });
});
```

## Правила

1. **Одна причина — один тест**; таблица — для вариантов одного поведения.
2. **Инъекция зависимостей** (fetch, время) — не мокируйте глобальные.
3. ✅ `assert/strict` (строгие сравнения), не `assert`.
4. ❌ `setTimeout`/`sleep` в тестах — фиксированное время через инъекцию.
5. ✅ Тестируйте ошибки: `assert.rejects`, не только happy path.

## Related

- [shared/testing.md](../../shared/testing.md)
- [../typescript/snippets/testing.md](../../typescript/snippets/testing.md) — vitest
