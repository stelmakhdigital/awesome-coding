---
id: c-strings
title: "C: строки (C23 stdstring.h, builder)"
lang: c
min_version: "C23"
category: snippet
tags: [strings, stdstring, cstr, buffer, builder]
status: stable
updated: 2026-09-06
---

# Строки (C23)

**Когда использовать** — любая работа со строками в C23.
**Когда НЕ использовать** — C17 (тогда `<string.h>` + явные размеры).

Код проверен на Apple clang 21 (`-std=c23 -Wall -Wextra -Werror`, выполнен, ASan-чисто).
`<stdstring.h>` — против совместимой реализации (C23-библиотека отсутствует в libc Darwin;
на GCC 14+/Linux заголовок штатный).

## stdstring.h (C23)

```c
#include <stdstring.h>
#include <stdio.h>

int main(void) {
    char buf[32];

    // Длина без учёта '\0'.
    const char *s = "hello";
    size_t n = cstr_length(s);
    printf("%zu\n", n); // 5

    // Копирование С размером буфера: гарантированно '\0'.
    cstr_copy(buf, sizeof(buf), "world");
    printf("%s\n", buf); // world

    // Конкатенация с размером.
    cstr_cat(buf, sizeof(buf), "!");
    printf("%s\n", buf); // world!

    // Поиск подстроки.
    const char *found = cstr_find("hello world", "world");
    printf("%s\n", found == NULL ? "nope" : found); // world

    // Сравнение (lexicographic).
    printf("%d\n", cstr_compare("abc", "abd") < 0); // 1

    return 0;
}
```

## Динамический builder

```c
#include <stdstring.h>
#include <stdlib.h>
#include <stdio.h>

// Простой growable-строковый буфер.
typedef struct {
    char *data;
    size_t len;
    size_t cap;
} StrBuilder;

int sb_init(StrBuilder *sb) {
    sb->cap = 32;
    sb->data = malloc(sb->cap);
    if (sb->data == NULL) return -1;
    sb->data[0] = '\0';
    sb->len = 0;
    return 0;
}

void sb_free(StrBuilder *sb) {
    free(sb->data);
    sb->data = NULL;
    sb->len = sb->cap = 0;
}

// Возвращает 0 / -1 (недостаточно памяти).
int sb_append(StrBuilder *sb, const char *s) {
    size_t n = cstr_length(s);
    if (sb->len + n + 1 > sb->cap) {
        size_t new_cap = sb->cap * 2;
        while (sb->len + n + 1 > new_cap) new_cap *= 2;
        char *p = realloc(sb->data, new_cap);
        if (p == NULL) return -1;
        sb->data = p;
        sb->cap = new_cap;
    }
    cstr_copy(sb->data + sb->len, sb->cap - sb->len, s);
    sb->len += n;
    return 0;
}

int main(void) {
    StrBuilder sb;
    if (sb_init(&sb) != 0) return 1;
    sb_append(&sb, "hello ");
    sb_append(&sb, "world");
    printf("%s (%zu)\n", sb.data, sb.len); // hello world (11)
    sb_free(&sb);
    return 0;
}
```

## Правила

1. ✅ **C23: `cstr_*`** — всегда с размером буфера (нет переполнений).
2. ❌ `strcpy`/`strcat`/`sprintf` — только `cstr_copy`/`cstr_cat`/`snprintf`.
3. ✅ Строка из API — `const char *`; мутация — только свои буферы.
4. ✅ Builder — для сборки строк (не `sprintf` в цикл).
5. ✅ Длина — `size_t`, не `int` (переполнение на больших строках).

## Related

- [rules.md](../rules.md)
- [memory.md](memory.md) — realloc
