---
id: c-rules
title: "C Rules"
lang: c
min_version: "C23"
category: rule-set
tags: [rules, guardrails, memory, safety, c23]
status: stable
updated: 2026-09-06
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

- ✅ C23: `<stdstring.h>` (`cstr_*`) — не «руками strlen/strcpy».
- ✅ Буферы — с явным размером; `cstr_copy(dst, dst_size, src)`.
- ❌ `strcpy`/`strcat`/`sprintf` без границ (переполнение).
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
- ✅ Одна функция — одна задача; < ~50 строк.
- ✅ `#pragma once` или include guards.
- ✅ Компиляция: `-std=c23 -Wall -Wextra -Werror` (+ санитайзеры в CI).

## Related

- [idioms.md](idioms.md) — идиомы
- [decisions.md](decisions.md) — выбор
- [shared/error-handling.md](../shared/error-handling.md)
