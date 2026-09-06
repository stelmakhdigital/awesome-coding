---
id: ts-idioms
title: "TypeScript Idioms"
lang: typescript
min_version: "7.0"
category: idioms
tags: [idioms, style, type-narrowing, generics, discriminated-unions]
status: stable
updated: 2026-09-06
---

# TypeScript Idioms — идиоматичный TS

Код проверен на tsc 7.0.2 (`strict: true`).

## Type narrowing

```ts
// Type guard: функция-предикат.
function isString(v: unknown): v is string {
  return typeof v === "string";
}

// Discriminated union: поле-дискриминатор.
type Shape =
  | { kind: "circle"; radius: number }
  | { kind: "rect"; width: number; height: number };

function area(s: Shape): number {
  switch (s.kind) {
    case "circle":
      return Math.PI * s.radius ** 2;
    case "rect":
      return s.width * s.height;
    // exhaustive check: если забыли ветку — ошибка компиляции
    default: {
      const _exhaustive: never = s;
      throw new Error(`unknown shape: ${JSON.stringify(_exhaustive)}`);
    }
  }
}
```

## satisfies и as const

```ts
// satisfies: проверяем тип, но сохраняем точный (узкий) тип значения.
const config = {
  port: 8080,
  host: "0.0.0.0",
  features: ["auth", "metrics"],
} satisfies {
  port: number;
  host: string;
  features: readonly string[];
};
// config.features — readonly ["auth", "metrics"], а не readonly string[]

const STATUS = {
  ACTIVE: "active",
  ARCHIVED: "archived",
} as const;
type Status = (typeof STATUS)[keyof typeof STATUS]; // "active" | "archived"
```

## Generics

```ts
// Идентичный тип вход/выход.
function first<T>(xs: readonly T[]): T | undefined {
  return xs[0];
}

// Ограничение типа.
function pluck<T, K extends keyof T>(xs: readonly T[], key: K): T[K][] {
  return xs.map((x) => x[key]);
}

// Инференс из аргументов (без явного указания типов).
function pair<T, U>(a: T, b: U): [T, U] {
  return [a, b];
}
```

## Template literal types

```ts
type EventName = "user" | "order";
type Event<E extends EventName> = `${E}:created` | `${E}:deleted`;

// Event<"user"> = "user:created" | "user:deleted"
```

## Async-идиомы

```ts
// withResolvers: промис с ручным resolve/reject.
export function waitForSignal(signal: AbortSignal): Promise<void> {
  const { promise, resolve, reject } = Promise.withResolvers<void>();
  signal.addEventListener(
    "abort",
    () => resolve(),
    { once: true },
  );
  return promise;
}

// Дебаунс.
export function debounce<A extends unknown[]>(
  fn: (...args: A) => void,
  ms: number,
): (...args: A) => void {
  let timer: ReturnType<typeof setTimeout> | undefined;
  return (...args: A) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}
```

## Related

- [rules.md](rules.md)
- [snippets/async.md](snippets/async.md) — таймауты, ретраи, лимиты
