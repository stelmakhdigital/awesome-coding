---
id: database-pagination
title: "Пагинация: OFFSET против keyset, непрозрачный курсор"
lang: database
min_version: "18"
category: snippet
tags: [postgres, pagination, keyset, cursor, offset, api]
status: stable
updated: 2026-11-24
---

# Пагинация (PostgreSQL)

**Когда использовать** — любой список, который может вырасти глубже первой
десятка страниц: лента, выгрузки, админки, очереди на обработку.
**Когда НЕ использовать** — гарантированно маленький список (настройки,
справочник на 30 строк) и случайный доступ по номеру страницы («страница 7407»
из UI): keyset так не умеет, и это та цена, за которую он не платит за глубину.

## Почему OFFSET — не «пока хватает»

```sql
-- Схема примеров ниже.
CREATE TABLE orders (
    id          bigserial PRIMARY KEY,
    status      text        NOT NULL DEFAULT 'unpaid',
    total_cents bigint      NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Порядок колонок = порядок сортировки списка, иначе индекс не помогает.
CREATE INDEX orders_status_created_idx ON orders (status, created_at DESC, id DESC);
```

```sql
-- Глубокая страница на OFFSET: брокер строк читает и выбрасывает 100000 строк.
-- Стоимость страницы растёт с глубиной, а «состав» страницы плывёт, если между
-- запросами вставили или удалили строку.
SELECT id, status, total_cents, created_at
  FROM orders
 ORDER BY status, created_at DESC, id DESC
 OFFSET 100000 LIMIT 20;
```

## Keyset: страница = «следующие N после последней строки»

```sql
-- Курсор — последняя строка предыдущей страницы. Стоимость не зависит от глубины:
-- индекс даёт диапазон, LIMIT ограничивает чтение.
-- Первая страница — тот же запрос с «курсора в начале времени»:
--   AND (created_at, id) > ('-infinity', 0)
-- Сравнение кортежей ((a, b) < (x, y)) — это и есть «по сортировке, tie-break по id».
SELECT id, status, total_cents, created_at
  FROM orders
 WHERE status = 'unpaid'
   AND (created_at, id) < ('2026-11-24 10:00:00+00', 900)
 ORDER BY created_at DESC, id DESC
 LIMIT 20;

-- «Есть ли следующая страница» отвечает лишняя строка (LIMIT N+1), а не COUNT(*)
-- над всем списком: count на большой таблице — это ещё один дорогой запрос.
SELECT id FROM orders WHERE status = 'unpaid'
 ORDER BY created_at DESC, id DESC LIMIT 21;
```

## Курсор для клиента (Go)

```go
// Package paging — keyset-страница с непрозрачным курсором для клиента.
package paging

import (
	"context"
	"database/sql"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"time"
)

// ErrBadCursor — курсор не распознан: мусор, другой список или другой сортировка.
var ErrBadCursor = errors.New("paging: bad cursor")

// Cursor — позиция последней отданной строки. Поля ровно те, что в ORDER BY,
// включая tie-break: без уникальной колонки курсор терял бы строки при равных
// значениях времени.
type Cursor struct {
	CreatedAt time.Time `json:"c"`
	ID        int64     `json:"i"`
}

// Encode — непрозрачный для клиента токен. Клиент не должен уметь его ни
// интерпретировать, ни подделать: при смене сортировки старые курсоры
// становятся невалидными, и это нормально (ErrBadCursor).
func (c Cursor) Encode() string {
	b, _ := json.Marshal(c) // time + int64 сериализуются всегда
	return base64.RawURLEncoding.EncodeToString(b)
}

// DecodeCursor — пустая строка означает «первая страница».
func DecodeCursor(s string) (Cursor, error) {
	if s == "" {
		return Cursor{}, nil
	}
	raw, err := base64.RawURLEncoding.DecodeString(s)
	if err != nil {
		return Cursor{}, ErrBadCursor
	}
	var c Cursor
	if err := json.Unmarshal(raw, &c); err != nil || c.ID == 0 || c.CreatedAt.IsZero() {
		return Cursor{}, ErrBadCursor
	}
	return c, nil
}

// Order — элемент списка.
type Order struct {
	ID        int64
	Status    string
	Total     int64
	CreatedAt time.Time
}

// Page — страница. NextCursor пуст, если следующей страницы нет.
type Page struct {
	Items      []Order
	NextCursor string
}

// Orders — одна страница «новее курсора». nil-курсор = первая страница: условие
// с IS NULL не даёт предикату отбросить всё начало списка.
func Orders(ctx context.Context, db *sql.DB, status string, cur Cursor, n int) (Page, error) {
	if n <= 0 || n > 200 {
		n = 50 // размер задаёт сервер: клиент не просит «всё сразу»
	}

	var curTime any
	var curID any
	if !cur.CreatedAt.IsZero() {
		curTime, curID = cur.CreatedAt, cur.ID
	}

	rows, err := db.QueryContext(ctx,
		`SELECT id, status, total_cents, created_at
		   FROM orders
		  WHERE status = $1
		    AND ($2::timestamptz IS NULL OR (created_at, id) < ($2, $3))
		  ORDER BY created_at DESC, id DESC
		  LIMIT $4`, status, curTime, curID, n+1)
	if err != nil {
		return Page{}, fmt.Errorf("query orders: %w", err)
	}
	defer rows.Close()

	var out []Order
	for rows.Next() {
		var o Order
		if err := rows.Scan(&o.ID, &o.Status, &o.Total, &o.CreatedAt); err != nil {
			return Page{}, fmt.Errorf("scan orders: %w", err)
		}
		out = append(out, o)
	}
	if err := rows.Err(); err != nil {
		return Page{}, fmt.Errorf("rows orders: %w", err)
	}

	page := Page{Items: out}
	if len(out) > n { // лишняя строка: она есть -> следующая страница есть
		page.Items = out[:n]
		last := page.Items[len(page.Items)-1]
		page.NextCursor = Cursor{CreatedAt: last.CreatedAt, ID: last.ID}.Encode()
	}
	return page, nil
}
```

## Правила

1. **Сортировка со стабильным tie-break** (`ORDER BY created_at DESC, id DESC`):
   без уникальной колонки-добавки курсор теряет или дублирует строки.
2. **Индекс под порядок страницы**: колонки фильтра, затем колонки сортировки в том
   же направлении. Иначе keyset тоже уйдёт в Sort.
3. **Размер страницы задаёт сервер**, максимум ограничен; `limit=100000` от клиента —
   это DoS, а не пагинация.
4. **Курсор непрозрачен**: клиент видит токен, а не `created_at` — можно менять
   внутреннее представление, не ломая клиентов.
5. **`hasMore` вместо `total_pages`**: точное число страниц требует `COUNT(*)` над
   всем фильтром на каждый запрос.
6. **Фильтр — часть курсора** (или валидируйте его): курсор от «unpaid», применённый
   к «paid», отдаёт пустую страницу без ошибки.

## Pitfalls

- **OFFSET после вставок**: элемент уезжает со страницы на страницу, пользователь
  видит дубль и пропуск. Keyset тоже «сдвигается», но без пропусков относительно
  своей позиции.
- **`COUNT(*)` ради «всего N страниц»** на каждой странице списка: на 50 млн строк
  это дороже самого списка. Нужна точная цифра — считайте отдельно и с кэшем.
- **Курсор без tie-break** (`created_at` не уникален): строки с одинаковым
  временем попадают в обе страницы или ни в одну.
- **Сортировка по колонке, которую обновили**: страница «до 10:00» после апдейта
  `created_at` теряет строку навсегда. Либо сортировка по неизменяемому полю,
  либо `(updated_at, id)` с принудительным `WHERE updated_at <= курса` — и там,
  и там нужны обоснования; проще не сортировать по изменяемому.
- **Свой формат курсора «дата_и_id через подчёркивание»**: ломается на первом же
  расширении сортировки; структура + JSON + base64 дешевле в поддержке.
- **Разные сортировки одним курсором**: нужен либо признак сортировки в токене,
  либо отказ (`ErrBadCursor`) — иначе пустые страницы без объяснения причины.

## Related

- [postgres-core.md](postgres-core.md) — индексы и EXPLAIN под этот запрос
- [../go/snippets/sql.md](../../go/snippets/sql.md) — `database/sql`, Rows, ошибки
- [../shared/api-design.md](../../shared/api-design.md) — курсор в контракте API
- [../shared/security.md](../../shared/security.md) — параметры вместо склейки строк
