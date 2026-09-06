---
id: ts-json
title: "TypeScript: JSON (zod, unknown на границе)"
lang: typescript
min_version: "7.0"
category: snippet
tags: [json, zod, validation, serialization, api]
status: stable
updated: 2026-09-06
---

# JSON (TypeScript)

**Когда использовать** — парсинг/сериализация JSON с границ (API, env, файлы).
**Когда НЕ использовать** — внутренний код, где данные уже типизированы.

Код проверен на tsc 7.0.2 (`strict: true`).

## Zod: схема + тип + парсинг

```ts
import { z } from "zod";

// Схема — источник истины; тип выводится.
const OrderSchema = z.object({
  id: z.string().uuid(),
  total: z.number().int().nonnegative(),
  status: z.enum(["new", "confirmed", "shipped"]),
  createdAt: z.coerce.date(),
});

export type Order = z.infer<typeof OrderSchema>;

// safeParse: результат — union, не исключение.
export function parseOrder(raw: unknown): Order {
  const result = OrderSchema.safeParse(raw);
  if (!result.success) {
    const details = result.error.issues
      .map((i) => `${i.path.join(".")}: ${i.message}`)
      .join("; ");
    throw new Error(`invalid order: ${details}`);
  }
  return result.data;
}

// Сериализация: Date -> ISO (JSON не умеет Date).
export function serializeOrder(o: Order): string {
  return JSON.stringify(o, (_k, v) => (v instanceof Date ? v.toISOString() : v));
}
```

## Без зависимостей: type guards

```ts
// Граница: unknown -> сужение.
function isOrder(v: unknown): v is { id: string; total: number } {
  return (
    typeof v === "object" &&
    v !== null &&
    typeof (v as Record<string, unknown>).id === "string" &&
    typeof (v as Record<string, unknown>).total === "number"
  );
}

export function parseOrderPlain(raw: unknown): { id: string; total: number } {
  if (!isOrder(raw)) {
    throw new Error("invalid order");
  }
  return raw; // здесь raw уже сужен до { id: string; total: number }
}
```

## Правила

1. **`unknown` на границе** — никогда не `JSON.parse` в `as T` без проверки.
2. ✅ `safeParse` (union) в коде, `parse` (throw) — только на границе с обработкой.
3. ✅ `z.coerce.date()` для ISO-строк; сериализация — с replacer для Date.
4. ❌ `any` после `JSON.parse`.
5. ✅ Схема — в одном месте, тип — `z.infer` (не дублировать).

## Related

- [shared/api-design.md](../../shared/api-design.md)
- [rules.md](../rules.md)
