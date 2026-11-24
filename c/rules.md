---
id: c-rules
title: "C Rules"
lang: c
min_version: "C23"
category: rule-set
tags: [rules, guardrails, memory, safety, c23]
status: stable
updated: 2026-11-24
---

# C Rules — обязательные правила

## Память

- ✅ **Один владелец** на каждый блок: кто выделил — тот освобождает (документируется в комментарии/имени).
- ✅ `NULL` после `free` (указатель не вешается).
- ✅ Все пути выхода функции освобождают выделенное (паттерн `goto cleanup`, см. [snippets/memory.md](snippets/memory.md)).
- ❌ Двойной `free`, утечки, use-after-free — санитайзеры (`-fsanitize=address,undefined`) в CI.
- ✅ `calloc` для массивов (обнуление), `malloc` — когда нужно.
- ✅ Размер — `size_t`, арифметика размеров — с проверкой переполнения.

## Строки

- ✅ Размер буфера рядом с операцией: `snprintf(buf, sizeof buf, …)`, `memcpy(dst, src, n)` + `dst[n] = '\0'`.
- ✅ `snprintf` проверяет усечение: вернулось `n >= size` — строка обрезана, это ошибка.
- ❌ `strcpy`/`strcat`/`sprintf` без границ (переполнение).
- ❌ `strncpy(dst, src, n)` как «безопасный strcpy» — не ставит `'\0'`, если `src` длиннее `n`.
- ❌ `#include <stdstring.h>` и `cstr_*` — в C23 этого нет (bounds-checked API — план C2y), код не соберётся.
- ✅ Строка в C — `const char *`, если не мутатируется.

## Типы и константность

- ✅ `const` — на всех входных параметрах-строках/структурах.
- ✅ `[[nodiscard]]` (C23) — на функциях, возвращающих ошибку/значение.
- ✅ `bool` из `<stdbool.h>`, не `int` для флага.
- ✅ `nullptr` (C23) — не `NULL`/`0` (где поддерживается).
- ✅ `_Static_assert` — инварианты размеров/выравнивания.

## Ошибки

- ✅ Коды возврата (`int`/`enum`) + `errno` для системных вызовов.
- ✅ Проверка **каждого** системного вызова и выделение (`malloc` → `NULL`).
- ❌ «Пустая» проверка `if (!p)` без обработки.
- ✅ `[[nodiscard]]` на функциях с кодом ошибки.

## Стиль

- ✅ Имена: `snake_case`; типы — `snake_case_t` (или `PascalCase` — единообразно).
- ✅ Макросы: `UPPER_SNAKE_CASE` (`MAX_ITEMS`); глобальные переменные — с префиксом модуля (`storage_init`).
- ✅ Одна функция — одна задача; < ~50 строк.
- ✅ `#pragma once` или include guards.
- ✅ Компиляция: `-std=c23 -Wall -Wextra -Werror` (+ санитайзеры в CI).

## Безопасность

- ✅ C23: bounded-функции (`strcpy_s`, `sprintf_s` — Annex K в стандарте); без `gets`.
- ✅ Границы: `strnlen`/`snprintf`/`memcpy` с проверкой размера; проверка переполнения
  до аллокации (`size > SIZE_MAX - offset`).
- ✅ Форматные строки — только константы (`printf("%s", s)`); `printf(user_input)` —
  format string attack.
- ✅ Сборка: `-fstack-protector-strong -D_FORTIFY_SOURCE=2 -fPIE -pie`; ASan/UBSan в CI.
- ❌ `system()`/`popen()` с внешним вводом (shell injection).

## Related

- [idioms.md](idioms.md) — идиомы
- [decisions.md](decisions.md) — выбор
- [shared/error-handling.md](../shared/error-handling.md)
