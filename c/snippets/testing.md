---
id: c-testing
title: "C: Testing (harness + assert, санитайзеры)"
lang: c
min_version: "C23"
category: snippet
tags: [testing, assert, harness, sanitizers, unit-tests]
status: stable
updated: 2026-09-06
---

# Testing (C)

**Когда использовать** — unit-тесты C-кода без внешних зависимостей.
**Когда НЕ использовать** — интеграция с реальными сервисами (отдельный бинарник).

Код проверен на Apple clang 21 (`-std=c23 -Wall -Wextra -Werror`, выполнен; ASan-чисто).

## Мини-harness

```c
#include <stdio.h>
#include <stdlib.h>

// Простой harness: регистрация тестов, счётчик провалов.
#define TEST(name) static void name(void)
#define RUN(name) \
    do { \
        printf("  %s ... ", #name); \
        name(); \
        printf("ok\n"); \
    } while (0)

#define CHECK(cond) \
    do { \
        if (!(cond)) { \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            exit(1); \
        } \
    } while (0)

// Код под тестом.
int clamp(int x, int lo, int hi) {
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

TEST(clamp_basic) {
    CHECK(clamp(5, 0, 10) == 5);
    CHECK(clamp(-1, 0, 10) == 0);
    CHECK(clamp(11, 0, 10) == 10);
}

TEST(clamp_equal_bounds) {
    CHECK(clamp(5, 3, 3) == 3);
}

int main(void) {
    RUN(clamp_basic);
    RUN(clamp_equal_bounds);
    printf("all tests passed\n");
    return 0;
}
```

## Табличные тесты

```c
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>

int parse_int(const char *s, int *out) {
    char *end = NULL;
    long v = strtol(s, &end, 10);
    if (end == s || *end != '\0') return -1;
    if (v < INT_MIN || v > INT_MAX) return -1;
    *out = (int)v;
    return 0;
}

typedef struct {
    const char *input;
    int expected_code;
    int expected_value;
} Case;

const Case cases[] = {
    {"42", 0, 42},
    {"-7", 0, -7},
    {"abc", -1, 0},
    {"", -1, 0},
    {"99999999999", -1, 0}, // переполнение int
};

int main(void) {
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        int v = 0;
        int code = parse_int(cases[i].input, &v);
        if (code != cases[i].expected_code || (code == 0 && v != cases[i].expected_value)) {
            fprintf(stderr, "FAIL case %zu: input=%s code=%d v=%d\n", i, cases[i].input, code, v);
            return 1;
        }
    }
    printf("all cases passed\n");
    return 0;
}
```

## Компиляция и запуск

```sh
# Строго + санитайзеры (обязательно в CI):
clang -std=c23 -Wall -Wextra -Werror -fsanitize=address,undefined test.c -o test
./test

# Фазер (парсеры/форматы):
clang -std=c23 -fsanitize=fuzzer,address fuzz_target.c -o fuzzer
./fuzzer
```

## Правила

1. ✅ **CHECK с файлом/строкой** — падение сразу говорит, где.
2. ✅ Табличные тесты — для вариантов (один harness, много данных).
3. ✅ ASan + UBSan — всегда (память + UB).
4. ✅ Тестируйте ошибки: коды возврата, `NULL`, переполнения.
5. ❌ `assert` в production-коде (вырезается с `NDEBUG`) — только в тестах.

## Related

- [shared/testing.md](../../shared/testing.md)
- [memory.md](memory.md) — санитайзеры
