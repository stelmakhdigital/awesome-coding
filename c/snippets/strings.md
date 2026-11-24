---
id: c-strings
title: "C: строки (размеры, snprintf, builder)"
lang: c
min_version: "C23"
category: snippet
tags: [strings, buffer, snprintf, memcpy, builder]
status: stable
updated: 2026-11-24
---

# Строки (C23)

**Когда использовать** — любая работа со строками в C.
**Когда НЕ использовать** — есть проверенный `char*`-контракт с известным размером:
тогда `memcpy` без терминатора.

**В C23 нет безопасной строковой библиотеки.** `stdstring.h` и `cstr_*` в стандарт не
вошли (bounds-checked API — план C2y), их нет ни в glibc, ни в musl, ни в libc Darwin:
код с `#include <stdstring.h>` не соберётся. Надёжность даёт только явный размер.
`[[null_terminated]]` и `_Countof` — действительно C23, но на gcc 14.3 не реализованы
(проверено: `-Werror=attributes`, `_Countof undeclared`), то есть в коде, который
собирается сегодня, их быть не должно.

## Базовые операции

```c
#include <stdio.h>
#include <string.h>

int main(void) {
    char buf[32] = "";
    const char *name = "world";

    // snprintf: не пишет больше размера и всегда ставит '\0'.
    int n = snprintf(buf, sizeof buf, "hello %s", name);
    if (n < 0 || (size_t)n >= sizeof buf) {
        return 1;                       // обрезано — это ошибка, а не «тихо неполная строка»
    }
    puts(buf);                          // hello world

    // Копирование с явным размером: memcpy + терминатор вручную.
    char copy[8];
    size_t len = strlen(name);
    size_t take = len < sizeof copy - 1 ? len : sizeof copy - 1;
    memcpy(copy, name, take);
    copy[take] = '\0';
    puts(copy);                         // world

    // Поиск и сравнение — только с длиной, а не «до '\0' на доверие».
    const char *found = strstr(buf, "world");
    puts(found != NULL ? found : "nope");                       // world
    printf("%d\n", strncmp("abc", "abd", 3) < 0);               // 1
    printf("%zu\n", strlen(name));                              // 5

    return 0;
}
```

## Динамический builder

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    char *data;
    size_t len;
    size_t cap;
} StrBuilder;

int sb_init(StrBuilder *sb) {
    sb->cap = 32;
    sb->data = malloc(sb->cap);
    if (sb->data == NULL) {
        return -1;
    }
    sb->data[0] = '\0';
    sb->len = 0;
    return 0;
}

void sb_free(StrBuilder *sb) {
    free(sb->data);
    sb->data = NULL;
    sb->len = 0;
    sb->cap = 0;
}

// 0 / -1 (память). Всегда держит терминатор в пределах cap.
int sb_append(StrBuilder *sb, const char *s) {
    size_t n = strlen(s);
    if (sb->len + n + 1 > sb->cap) {
        size_t want = sb->cap;
        while (sb->len + n + 1 > want) {
            want *= 2;
        }
        char *p = realloc(sb->data, want);
        if (p == NULL) {
            return -1;
        }
        sb->data = p;
        sb->cap = want;
    }
    memcpy(sb->data + sb->len, s, n);
    sb->len += n;
    sb->data[sb->len] = '\0';
    return 0;
}

int main(void) {
    StrBuilder sb;
    if (sb_init(&sb) != 0) {
        return 1;
    }
    if (sb_append(&sb, "hello ") != 0 || sb_append(&sb, "world") != 0) {
        sb_free(&sb);
        return 1;
    }
    printf("%s (%zu)\n", sb.data, sb.len);              // hello world (11)
    sb_free(&sb);
    return 0;
}
```

## Pitfalls
- `snprintf` возвращает **длина которой надо было**, а не записано: `n >= size` = обрезали.
- `strncpy(dst, src, n)` не терминирует, если `src` длиннее `n` — `memcpy` + `dst[k] = '\0'` честнее.
- `sprintf`/`strcpy`/`strcat` без размера — переполнение стека; в новом коде их нет.
- Builder без проверки `realloc` — утечка и запись в освобождённую память.
- `strlen` в цикле по той же строке — O(n²); длину считать один раз.

## Правила

1. ✅ Размер буфера — рядом с операцией (`sizeof buf`, не магическая константа).
2. ❌ `strcpy`/`strcat`/`sprintf` — только `snprintf` + `memcpy` с размером.
3. ✅ Строка из API — `const char *`; мутация — только свои буферы.
4. ✅ Builder — для сборки строк, не `strcat` в цикле.
5. ✅ Длина — `size_t`, не `int`.

## Related

- [rules.md](../rules.md)
- [memory.md](memory.md) — realloc
