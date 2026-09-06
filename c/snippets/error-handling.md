---
id: c-error-handling
title: "Error handling: коды возврата, errno, cleanup через goto"
lang: c
min_version: "C23"
category: snippet
tags: [errors, errno, cleanup, memory]
status: stable
updated: 2026-09-06
---

# Error handling

**Когда использовать** — любой C-код с аллокациями, файловыми/сетевыми операциями.
**Когда НЕ использовать** — не применимо: это базовый слой.

## Код

```c
// cleanup.c — идиома: один label, обратный порядок освобождения.
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct buffer {
    char *data;
    size_t len;
};

static void buffer_free(struct buffer *b)
{
    if (b != NULL) {
        free(b->data);
        b->data = NULL;
        b->len = 0;
    }
}

/* Возврат: 0 — успех, -1 — ошибка (errno установлен для системных ошибок). */
int process_file(const char *path, struct buffer *out)
{
    FILE *f = NULL;
    struct buffer buf = {0};
    int rc = -1;

    f = fopen(path, "rb");
    if (f == NULL) {
        goto done; /* errno установлен: errno.h */
    }

    if (fseek(f, 0, SEEK_END) != 0) {
        goto done;
    }
    long size = ftell(f);
    if (size < 0) {
        goto done;
    }
    rewind(f);

    buf.data = malloc((size_t)size + 1);
    if (buf.data == NULL) {
        goto done; /* ENOMEM */
    }
    if (fread(buf.data, 1, (size_t)size, f) != (size_t)size) {
        goto done;
    }
    buf.data[size] = '\0';
    buf.len = (size_t)size;

    *out = buf;
    rc = 0;

done:
    if (f != NULL) {
        fclose(f);
    }
    if (rc != 0) {
        buffer_free(&buf);
    }
    return rc;
}

int main(void)
{
    struct buffer buf = {0};
    if (process_file("input.txt", &buf) != 0) {
        fprintf(stderr, "process_file: %s\n", strerror(errno));
        return 1;
    }
    printf("read %zu bytes\n", buf.len);
    buffer_free(&buf);
    return 0;
}
```

## Pitfalls

- Проверяйте **каждый** возврат: `malloc`, `fopen`, `fread`, `strdup` и т.д.
- `errno` — устанавливайте/читайте только сразу после вызова; не вызывайте другие функции между ними.
- `goto done` — идиома, а не «плохой стиль»: единственный путь cleanup, обратный порядок освобождения.
- После неудачного `fread` проверьте `ferror`/`feof`, чтобы отличить ошибку от EOF.
- `[[nodiscard]]` (C23) — на функциях, чей результат нельзя игнорировать:
  `[[nodiscard]] int compute(void);`

## Related

- [shared/error-handling.md](../../shared/error-handling.md) — кросс-языковые принципы
