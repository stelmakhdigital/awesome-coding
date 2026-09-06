---
id: js-idioms
title: "JavaScript Idioms"
lang: javascript
min_version: "ES2025"
category: idioms
tags: [idioms, style, destructuring, iterators, es2025]
status: stable
updated: 2026-09-06
---

# JavaScript Idioms — идиоматичный JS (ES2025)

Код проверен на node v22.23.2 (выполнен).

## Деструктуризация и spread

```js
// Деструктуризация с дефолтами и переименованием.
function makeUser({ id, name = "anonymous", roles: roleList = [] } = {}) {
  return { id, name, roles: [...roleList] };
}

// Spread: иммутабельное обновление.
const config = { host: "localhost", port: 8080 };
const updated = { ...config, port: 9090 }; // config не мутится
```

## Optional chaining и nullish

```js
// ?. — цепочки без null-check; ?? — только null/undefined.
const user = { address: {} };
const city = user?.address?.city ?? "unknown";
const options = {};
const timeout = options.timeout ?? 30_000; // 0 — валидное значение!
console.log(city, timeout); // unknown 30000
```

## Iterators и iterator helpers (ES2024+)

```js
// Генераторы: ленивые последовательности.
function* range(from, to) {
  for (let i = from; i < to; i++) yield i;
}

// Iterator helpers (ES2024): map/filter/take на итераторах.
const evens = range(0, 10)
  .map((x) => x * 2)
  .filter((x) => x % 4 === 0)
  .take(3);
console.log([...evens]); // [0, 4, 8]
```

## Объекты и коллекции (ES2024/2025)

```js
// Object.groupBy: группировка в один проход.
const orders = [
  { id: 1, status: "new" },
  { id: 2, status: "new" },
  { id: 3, status: "shipped" },
];
const byStatus = Object.groupBy(orders, (o) => o.status);
console.log(byStatus.new.length); // 2

// structuredClone: глубокое клонирование без сериализации.
const copy = structuredClone(orders);
copy[0].id = 99;
console.log(orders[0].id); // 1

// Array.fromAsync: из async-итерабельного.
const urls = ["a", "b", "c"];
const fetchJson = async (u) => ({ url: u, ok: true });
const results = await Array.fromAsync(
  urls.map(async (u) => fetchJson(u)),
);
console.log(results.length); // 3
```

## Promise.withResolvers (ES2024)

```js
// Промис с ручным resolve/reject — без обёртки в new Promise.
export function waitForSignal(signal) {
  const { promise, resolve } = Promise.withResolvers();
  signal.addEventListener("abort", () => resolve(), { once: true });
  return promise;
}
```

## Правила

1. ✅ `??` вместо `||` для дефолтов (0/""/false — валидные значения).
2. ✅ Iterator helpers — вместо `[...arr].map().filter()` для больших данных (ленивость).
3. ✅ `structuredClone` — вместо `JSON.parse(JSON.stringify())`.
4. ❌ `Object.assign` для глубокого копирования (поверхностный).

## Related

- [rules.md](rules.md)
- [snippets/async.md](snippets/async.md) — таймауты, ретраи
