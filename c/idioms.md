---
id: c-idioms
title: "C Idioms (C23)"
lang: c
min_version: "C23"
category: idioms
tags: [idioms, style, c23, structs, static-assert]
status: stable
updated: 2026-09-06
---

# C Idioms (C23)

Код проверен на Apple clang 21 (`-std=c23 -Wall -Wextra -Werror`, выполнен).

## Структуры и init/cleanup

```c
#include <stdbool.h>
#include <stddef.h>
#include <stdalign.h>
#include <stdio.h>
#include <stdlib.h>

// Паттерн: конструктор возвращает struct (не указатель) — нет утечек.
typedef struct {
    int *items;
    size_t len;
    size_t cap;
} IntVec;

IntVec intvec_new(size_t cap) {
    IntVec v = {0};
    v.cap = cap;
    v.items = malloc(cap * sizeof(int));
    return v;
}

void intvec_free(IntVec *v) {
    free(v->items);
    v->items = NULL;
    v->len = v->cap = 0;
}

// Designated initializers (C99+) — читаемые константы.
const struct { int x, y, z; } ORIGIN = {.x = 0, .y = 0, .z = 0};

// _Static_assert: инварианты на этапе компиляции.
_Static_assert(alignof(IntVec) <= sizeof(void *), "IntVec must be pointer-aligned");

int main(void) {
    IntVec v = intvec_new(8);
    v.items[v.len++] = 42;
    printf("%d\n", v.items[0]); // 42
    intvec_free(&v);
    return 0;
}
```

## C23: auto, typeof, nullptr

```c
#include <stdio.h>
#include <stdalign.h>

// auto (C23): вывод типа, как в C++.
void demo_auto(void) {
    auto x = 42;          // int
    auto s = "hello";     // const char *
    (void)x; (void)s;
}

// typeof (C23): тип выражения.
void demo_typeof(int a, long b) {
    typeof(a) c = a;      // int
    typeof(b) d = b;      // long
    (void)c; (void)d;
}

// nullptr (C23): типизированный null-указатель.
int *p = nullptr;

int main(void) {
    demo_auto();
    demo_typeof(1, 2L);
    printf("%s\n", p == nullptr ? "null" : "not-null");
    return 0;
}
```

## [[nodiscard]] и bool

```c
#include <stdbool.h>
#include <stdio.h>

// [[nodiscard]] (C23): компилятор ругается, если игнорировать результат.
[[nodiscard]] int divide(int a, int b) {
    if (b == 0) return -1;
    return a / b;
}

[[nodiscard]] bool is_even(int x) {
    return x % 2 == 0;
}

int main(void) {
    int r = divide(10, 2); // ok: результат использован
    printf("%d %s\n", r, is_even(r) ? "even" : "odd");
    return 0;
}
```

## Compound literals и VLA-альтернатива

```c
#include <stdio.h>

// Compound literal: временный объект.
struct Point { double x, y; };

double dist(struct Point a, struct Point b) {
    double dx = a.x - b.x, dy = a.y - b.y;
    return dx * dx + dy * dy;
}

int main(void) {
    struct Point origin = {0.0, 0.0};
    struct Point p = {3.0, 4.0};
    printf("%.0f\n", dist(origin, p)); // 25
    return 0;
}
```

## Правила

1. ✅ Init/cleanup-пары (или struct-возврат) — не «указатель + вызовчик освобождает».
2. ✅ `_Static_assert` — инварианты размеров/выравнивания.
3. ✅ `auto`/`typeof`/`nullptr` (C23) — когда компилятор поддерживает.
4. ✅ `[[nodiscard]]` на всех функциях с кодами ошибок.

## Related

- [rules.md](rules.md)
- [snippets/memory.md](snippets/memory.md) — аллокация
