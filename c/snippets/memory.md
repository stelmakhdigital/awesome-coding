---
id: c-memory
title: "C: память (ownership, cleanup, arena)"
lang: c
min_version: "C23"
category: snippet
tags: [memory, malloc, cleanup, arena, ownership]
status: stable
updated: 2026-09-06
---

# Память (C)

**Когда использовать** — любая работа с `malloc`/выделением.
**Когда НЕ использовать** — статические/стековые объекты (аллокация не нужна).

Код проверен на Apple clang 21 (`-std=c23 -Wall -Wextra -Werror`, выполнен; ASan-чисто).

## Ownership и cleanup (goto-паттерн)

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Правило: один владелец (кто выделил — тот освобождает).
// Все ошибки — через goto cleanup: один путь освобождения.
typedef struct {
    char *name;
    int *values;
    size_t n;
} Config;

int config_load(const char *path, Config *out) {
    FILE *f = NULL;
    char *name = NULL;
    int *values = NULL;

    f = fopen(path, "r");
    if (f == NULL) return -1;

    name = malloc(64);
    values = malloc(1024 * sizeof(int));
    if (name == NULL || values == NULL) goto cleanup;

    // ... чтение из f ...
    *out = (Config){.name = name, .values = values, .n = 0};
    name = NULL;   // владение передано в *out
    values = NULL; // не освобождаем в cleanup
    fclose(f);
    f = NULL;
    return 0;

cleanup:
    if (f) fclose(f);
    free(name);
    free(values);
    return -1;
}
```

## Безопасный realloc

```c
#include <stddef.h>
#include <stdlib.h>

// realloc может вернуть NULL, не освободив старый блок:
// сохраняем указатель до переназначения.
int *grow(int *old, size_t old_cap, size_t new_cap) {
    if (new_cap <= old_cap) return old; // нечего делать
    int *p = realloc(old, new_cap * sizeof(int));
    if (p == NULL) {
        free(old); // старый блок валиден: освобождаем явно
        return NULL;
    }
    return p;
}
```

## Arena (bump) allocator

```c
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

// Один free на арену: для множества мелких объектов за одну операцию.
typedef struct {
    unsigned char *base;
    size_t size;
    size_t used;
} Arena;

Arena arena_new(size_t size) {
    unsigned char *base = malloc(size);
    return (Arena){.base = base, .size = size, .used = 0};
}

// Выравнивание: 8 байт (указатель).
void *arena_alloc(Arena *a, size_t size, size_t align) {
    size_t aligned = (a->used + align - 1) & ~(align - 1);
    if (aligned + size > a->size) return NULL; // переполнение
    void *p = a->base + aligned;
    a->used = aligned + size;
    return p;
}

void arena_free(Arena *a) {
    free(a->base);
    a->base = NULL;
    a->size = a->used = 0;
}

int main(void) {
    Arena a = arena_new(4096);
    int *x = arena_alloc(&a, sizeof(int), alignof(int));
    char *s = arena_alloc(&a, 32, alignof(char));
    *x = 7;
    (void)s;
    printf("%d\n", *x); // 7
    arena_free(&a);
    return 0;
}
```

## Правила

1. ✅ **Один владелец**; передача владения — через обнуление локального указателя.
2. ✅ `goto cleanup` — единый путь освобождения (не «free в каждом if»).
3. ✅ `realloc`: сохраняем старый указатель до `NULL`-проверки.
4. ✅ Arena — для «много мелких, живут одинаково долго».
5. ✅ ASan/UBSan в CI: утечки и переполнения ловятся автоматически.

## Related

- [rules.md](../rules.md)
- [error-handling.md](error-handling.md) — коды возврата
