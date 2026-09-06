---
id: js-json
title: "JavaScript: JSON (валидация, structuredClone, Date)"
lang: javascript
min_version: "ES2025"
category: snippet
tags: [json, validation, structured-clone, api]
status: stable
updated: 2026-09-06
---

# JSON (JavaScript)

**Когда использовать** — парсинг/сериализация JSON с границ (API, env, файлы).
**Когда НЕ использовать** — внутренний код с уже валидными данными.

Код проверен на node v22.23.2 (выполнен).

## Валидация без зависимостей

```js
// Граница: unknown -> валидация -> объект.
export function parseOrder(raw) {
  if (typeof raw !== "object" || raw === null) {
    throw new Error("invalid order: not an object");
  }
  const { id, total, status } = raw;
  if (typeof id !== "string" || id.length === 0) {
    throw new Error("invalid order: id");
  }
  if (typeof total !== "number" || !Number.isInteger(total) || total < 0) {
    throw new Error("invalid order: total");
  }
  if (!["new", "confirmed", "shipped"].includes(status)) {
    throw new Error(`invalid order: status=${String(status)}`);
  }
  // Возвращаем только ожидаемые поля (не «всё, что пришло»).
  return { id, total, status };
}
```

## Сериализация с Date

```js
// JSON не умеет Date: replacer + reviver.
const replacer = (_key, value) => (value instanceof Date ? value.toISOString() : value);
const reviver = (_key, value) =>
  typeof value === "string" && /^\d{4}-\d{2}-\d{2}T/.test(value) ? new Date(value) : value;

export function serializeOrder(o) {
  return JSON.stringify(o, replacer);
}

export function deserializeOrder(s) {
  return JSON.parse(s, reviver);
}
```

## Глубокое клонирование

```js
// structuredClone: без сериализации, поддерживает Map/Set/Symbol.
const original = { orders: [{ id: 1 }], tags: new Set(["a"]) };
const copy = structuredClone(original);
copy.orders[0].id = 99;
console.log(original.orders[0].id); // 1
```

## Правила

1. ✅ **Валидация на границе**: `JSON.parse` → проверка типов → объект с ожидаемыми полями.
2. ❌ `JSON.parse` «и поехали» без проверки (внешние данные — враг).
3. ✅ `structuredClone` — вместо `JSON.parse(JSON.stringify())` (Date/Symbol/циклы — не переживут JSON).
4. ✅ Date — только через replacer/reviver (ISO-строки в JSON).

## Related

- [shared/api-design.md](../../shared/api-design.md)
- [../typescript/snippets/json.md](../../typescript/snippets/json.md) — zod
