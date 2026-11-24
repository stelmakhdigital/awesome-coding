---
id: database-dialect-portability
title: "Две СУБД в одном коде: SQLite в тестах, PostgreSQL в проде"
lang: database
min_version: null
category: snippet
tags: [sqlite, postgres, dialect, portability, testing, pure-go, embed, parity, migration]
status: stable
updated: 2026-11-25
---

# Две СУБД в одном коде: SQLite в тестах, PostgreSQL в проде

**Когда использовать** — тесты и локальный запуск должны работать без контейнера (быстро, офлайн, в CI без docker), а в проде — PostgreSQL. Тот же код, две ссылки на базу.
**Когда НЕ использовать** — если в проде SQLite и точка (тогда SQLite и в тестах, и весь этот раздел не про вас); если в проде что-то, кроме PostgreSQL (список расхождений другой); если запросы на 70 экранов — содержательнее сделать один движок и в тестах (testcontainers против настоящего Postgres), чем держать совместимость.

## Чем это кончается, если не делать специально

| Область | PostgreSQL | SQLite | Как выглядит баг |
|---|---|---|---|
| Внешние ключи | включены | **выключены по умолчанию** (`PRAGMA foreign_keys`) | тесты зелёные, «удалил пользователя — осиротели сессии» только в проде… или наоборот: в тесте со включённым pragma падает то, что в проде работает |
| Типы колонки | строгие | affinity: в `INTEGER` можно записать строку | мусорные данные, которые Postgres бы не принял |
| Placeholder | `$1` | `?` | подстановка «заменой `?` на `$n`» ломается на `?` внутри строкового литерала |
| Автоключ | `GENERATED ALWAYS AS IDENTITY` | `INTEGER PRIMARY KEY` (rowid) | `RETURNING id` — общий, а вот объявление колонки — нет |
| `NULL`-сравнение | `IS DISTINCT FROM` | `IS NOT` (и `IS`) | запрос уезжает на другую ветку плана или не парсится |
| Регулярки | `~`, `~*` | нет | условие «фильтр по шаблону» работает только в проде |
| JSON | `jsonb`, индексы, `->>` | `json_extract` | одинаковый результат не гарантирован на краевых значениях |
| Дата/время | `timestamptz`, часы | TEXT/REAL, часовых поясов нет | «сегодня» расходится на границе суток |
| `ALTER TABLE` | почти всё | только переименование и добавление колонки | миграция, прошедшая на SQLite-стадии, неработоспособна на Postgres-стадии |
| Запись одновременно | много писателей | один писатель: второй получает `SQLITE_BUSY` | тесты в `t.Parallel()` падают «иногда» |
| Транзакция для записи | обычный `BEGIN` | отложенный `BEGIN` → upgrade-дедлок | та же гонка ведёт себя по-разному |
| `LIKE` без регистра | зависит от collation | ASCII-only | «Найти по имени» находит «ИВАН» в Postgres и не находит в SQLite |

Полный отказ от расхождений — тоже решение: один движок везде. Плохо другое — когда расхождения обнаруживаются в проде.

## Запросы по диалекту, без переписывания текста

```go
// Package store — доступ к базе, которая может быть SQLite или PostgreSQL.
// Расхождения диалектов закрыты списком операторов на диалект, а не
// подстановкой плейсхолдеров.
package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
)

type Dialect int

const (
	SQLite Dialect = iota
	Postgres
)

// Store — единственная точка, где про диалект помнят.
type Store struct {
	db    *sql.DB
	dial  Dialect
	stmts map[string]string // ключ -> SQL, собранный под конкретный диалект
}

// Опросы отличаются тем, чего второй движок не умеет: NULL-сравнение и
// регистронезависимый поиск. Ключ один и тот же, текст — разный.
var queries = map[Dialect]map[string]string{
	SQLite: {
		"openSessionsByUser": `
SELECT s.id, s.stage
FROM sessions AS s
WHERE s.user_id = ?
  AND s.closed_at IS NOT
ORDER BY s.started_at DESC
LIMIT 20`,
		"searchTasks": `
SELECT id, title FROM tasks
WHERE title LIKE ? ESCAPE '\'
ORDER BY id`,
	},
	Postgres: {
		"openSessionsByUser": `
SELECT s.id, s.stage
FROM sessions AS s
WHERE s.user_id = $1
  AND s.closed_at IS DISTINCT FROM NULL
ORDER BY s.started_at DESC
LIMIT 20`,
		"searchTasks": `
SELECT id, title FROM tasks
WHERE title ILIKE ? ESCAPE '\'
ORDER BY id`,
	},
}

func New(db *sql.DB, dial Dialect) (*Store, error) {
	set, ok := queries[dial]
	if !ok {
		return nil, errors.New("store: неизвестный диалект")
	}
	return &Store{db: db, dial: dial, stmts: set}, nil
}

// Query — доступ по ключу. Молча подставить «чужой» текст запроса нельзя:
// это тот самый баг, который ищем в другом диалекте.
func (s *Store) Query(ctx context.Context, key string, args ...any) (*sql.Rows, error) {
	q, ok := s.stmts[key]
	if !ok {
		return nil, fmt.Errorf("store: запрос %q не описан для диалекта %d", key, s.dial)
	}
	return s.db.QueryContext(ctx, q, args...)
}

// EscapeLike — одинаковый текст шаблона для обоих движков: `_` и `%` в вводе
// пользователя экранируются одинаково, различается только регистронезависимость.
func EscapeLike(v string) string {
	v = strings.ReplaceAll(v, `\`, `\\`)
	v = strings.ReplaceAll(v, `%`, `\%`)
	return strings.ReplaceAll(v, `_`, `\_`)
}
```

Переписывать `?` в `$1…$n` текстом — типичная самоделка, которая падает на литерале с вопросительным знаком и на `$` внутри строки. Два текста запроса скучнее, зато каждый исполняется, а не «может исполниться».

## Подключение и настройки

```go
package store

import (
	"database/sql"
	"fmt"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib" // драйвер pgx под database/sql
	_ "modernc.org/sqlite"             // SQLite без cgo
)

// OpenSQLite — база в файле (или :memory:). Прагмы идут в DSN: включить их
// «потом, первым запросом» — значит потерять то соединение из пула, на котором
// запрос уже ушёл на другой коннект.
func OpenSQLite(path string) (*sql.DB, error) {
	dsn := fmt.Sprintf(
		"file:%s?_pragma=busy_timeout(5000)&_pragma=foreign_keys(1)&_pragma=journal_mode(WAL)",
		path,
	)
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("sqlite open: %w", err)
	}
	// Один писатель: больше одного соединения — очередь на запись и SQLITE_BUSY
	// вместо ожидаемого терпения busy_timeout.
	db.SetMaxOpenConns(1)
	db.SetConnMaxLifetime(time.Hour)
	return db, nil
}

// OpenPostgres — прод. Имя драйвера «pgx» регистрирует импорт stdlib-пакета.
func OpenPostgres(dsn string) (*sql.DB, error) {
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		return nil, fmt.Errorf("postgres open: %w", err)
	}
	db.SetMaxOpenConns(16)
	db.SetMaxIdleConns(8)
	db.SetConnMaxIdleTime(5 * time.Minute)
	return db, nil
}

```text
// Схема на каждый диалект лежит рядом с кодом и вшивается в бинарник:
// «в тесте не нашлось migrations/» перестаёт быть возможным отказом.

//go:embed schema_sqlite.sql
var schemaSQLite string

//go:embed schema_postgres.sql
var schemaPostgres string

func Schema(d Dialect) string {
	if d == Postgres {
		return schemaPostgres
	}
	return schemaSQLite
}
```

`//go:embed` требует, чтобы файл существовал в той же директории: держите обе схемы рядом и сверяйте тестом на паритет (ниже), иначе они разъедутся в первую же миграцию.

## Тест на паритет

Не «тесты на SQLite + тесты на Postgres по отдельности», а один и тот же набор кейсов на обеих базах, с одним списком ожиданий:

```text
1. Открыть обе базы, накатить свои схемы.
2. Прогнать сценарий: вставка → чтение → обновление → уникальность → FK-каскад.
3. Краевые случаи, где движки расходятся:
   - NULL против пустой строки;
   - регистронезависимый поиск на не-ASCII;
   - сортировка строк с диакритикой (collation);
   - вставка строки в INTEGER-колонку (SQLite пропустит);
   - две параллельные записи (SQLite — busy_timeout, Postgres — обе пройдут).
4. Сравнить результаты; расхождение — задокументированное или исправленное.
```

Сценарий общий, отличаются только подключения. Расхождения из шага 3 заносятся в список «мы так сознательно решили»: «уникальность по email проверяется в приложении, потому что на SQLite…», — иначе через полгода новый человек примет их за баг.

## Правила, которые держат конструкцию

- Расхождения закрываются **выбором текста запроса по диалекту**, а не переписыванием строк и не «ORM всё спрячет»: ORM прячет до первого `ILIKE`.
- Оба диалекта проверяются на сборке и в CI. Тесты, которые «на этой машине не гоняются», умирают за неделю.
- Миграции пишутся так, чтобы каждая работала на обеих СУБД, либо парой файлов. `ALTER TABLE … ALTER COLUMN` — тест на то, что вы про SQLite забыли.
- Прагмы и пул: SQLite — `foreign_keys=1`, `busy_timeout`, `journal_mode=WAL`, `SetMaxOpenConns(1)`; PostgreSQL — лимиты пула по числу свободных мест на сервере, а не «по умолчанию».
- Даты — `TEXT` в ISO-8601 с зоной в SQLite и `timestamptz` в Postgres, и ни там ни там «локальное время без зоны».
- Чистая проверка «а не соврёт ли SQLite» — тест, который гоняет те же кейсы против Postgres в контейнере. Один такой тест на критичный сценарий дешевле, чем половина этого раздела.

## Related

- [postgres-core.md](postgres-core.md) — типы, `RETURNING`, `psql`-привычки
- [migrations.md](migrations.md) — миграции, expand/contract, откат
- [transactions.md](transactions.md) — уровни изоляции и блокировки: на SQLite их почти нет
- [../../go/snippets/sql.md](../../go/snippets/sql.md) — `database/sql`, пул, `pgx`
- [../../go/snippets/testing.md](../../go/snippets/testing.md) — тесты с `t.Parallel()` и общая база
