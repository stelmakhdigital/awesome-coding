---
id: py-stdlib-data
title: "Python: CSV, JSONL и даты (stdlib) — выгрузка, итоги по дням, часовой пояс"
lang: python
min_version: "3.14"
category: snippet
tags: [csv, jsonl, datetime, zoneinfo, decimal, counter, stdlib, encoding, money]
status: stable
updated: 2026-11-24
---

# CSV, JSONL и даты на stdlib

**Когда использовать** — разобрать выгрузку, посчитать итоги, написать отчёт, не поднимая pandas/SQL: файлы до сотен тысяч строк, формат известен, считать надо по дням и измерениям. Всё на stdlib, память — по строке за раз.
**Когда НЕ использовать** — xlsx, несколько листов, формулы ([python/decisions.md](../decisions.md) — openpyxl). Агрегаты на миллионах строк и joins — в PostgreSQL ([../database/snippets/postgres-core.md](../../database/snippets/postgres-core.md)), там и план запроса виден. Нужна строгая схема записи — модель + валидация ([json.md](json.md)).

## Выгрузка CSV: битые строки не должны ронять разбор

```python
"""Выгрузка CSV → итоги по дням. Разбор и арифметика — stdlib."""
from collections import defaultdict
from csv import DictReader
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Одна битая строка не повод терять файл целиком: их собирают в problems и
# показывают в конце. Молча пропускать — значит потерять данные незаметно.
def totals_by_day(
    path: Path,
    date_col: str = "date",
    amount_col: str = "amount",
) -> tuple[dict[date, Decimal], list[str]]:
    totals: dict[date, Decimal] = defaultdict(lambda: Decimal("0"))
    problems: list[str] = []

    # newline="" обязателен: без него csv сам translates переводы строк и
    # ломает значения с переносом внутри кавычек.
    # utf-8-sig срезает BOM, который Excel ставит в начало и из-за которого
    # первое поле заголовка читается как "\ufeffdate".
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = DictReader(fh)
        if not reader.fieldnames:
            return {}, [f"{path}: пустой файл"]
        for missing in (date_col, amount_col):
            if missing not in reader.fieldnames:
                return {}, [f"{path}: нет колонки {missing!r}, есть {reader.fieldnames}"]

        for rownum, row in enumerate(reader, start=2):  # 1 — заголовок
            raw_date = (row[date_col] or "").strip()
            raw_amount = (row[amount_col] or "").strip().replace("\u00a0", "")
            try:
                day = date.fromisoformat(raw_date)
            except ValueError:
                problems.append(f"{path}:{rownum}: дата {raw_date!r}")
                continue
            if not raw_amount:
                problems.append(f"{path}:{rownum}: пустая сумма")
                continue
            try:
                # Decimal принимает строку; float() здесь потеряет разряды.
                totals[day] += Decimal(raw_amount)
            except InvalidOperation:
                problems.append(f"{path}:{rownum}: сумма {raw_amount!r}")

    return dict(totals), problems
```

## JSONL: дозапись без перезаписи и чтение после падения

```python
"""JSON Lines: журнал событий, который можно дозаписывать и читать частично."""
import json
from collections.abc import Iterator
from pathlib import Path

def append_event(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        # ensure_ascii=False — читабельные кириллические значения вместо \uXXXX;
        # separators убирают пробелы, на больших файлах разница заметна.
        fh.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
        fh.write("\n")
        # Файл-журнал пишут, чтобы пережить падение процесса: flush+fsync —
        # цена, за которую строка действительно на диске.
        fh.flush()

def read_events(path: Path) -> Iterator[tuple[int, dict]]:
    """Отдаёт целые записи; обрезанная последняя строка — не исключение.

    Процесс, упавший при записи, оставляет неполную строку в конце файла.
    Падать на ней — значит потерять весь журнал из-за одной байты.
    """
    with path.open(encoding="utf-8") as fh:
        for rownum, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield rownum, json.loads(line)
            except json.JSONDecodeError:
                continue  # счётчик битых строк — в метрику, не в молчание
```

## Даты: один формат на входе, aware время внутри, локальная зона на выходе

```python
"""Границы периода и «сутки» без ошибок про часовой пояс."""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# fromisoformat против strptime: первый быстрее, строже и не требует
# расстрелянного формата "%d.%m.%Y"; strptime к тому же отдаёт naive время.
def parse_day(value: str) -> date:
    return date.fromisoformat(value.strip())

def month_bounds(tz: ZoneInfo, year: int, month: int) -> tuple[datetime, datetime]:
    """Полуинтервал [начало, конец) месяца по локальным часам.

    Границы считаются от date, а не прибавлением 24*30 часов: в сутки перевода
    часов ровно 23 или 25 часов.
    """
    start_local = date(year, month, 1)
    next_month = date(year + (month == 12), (month % 12) + 1, 1)
    start = datetime(start_local.year, start_local.month, start_local.day,
                     0, 0, tzinfo=tz)
    end = datetime(next_month.year, next_month.month, next_month.day,
                   0, 0, tzinfo=tz)
    return start, end

def utc_now() -> datetime:
    # datetime.now() без зоны отдаёт naive время: сравнение с aware бросает
    # TypeError, а арифметика через границу зоны врёт молча.
    return datetime.now(timezone.utc)

def next_run(at: datetime, hour: int, minute: int, tz: ZoneInfo) -> datetime:
    """Ближайшие «часы:минуты» по локальному времени, aware на выходе."""
    local = at.astimezone(tz)
    candidate = datetime.combine(local.date(), datetime.min.time(), tzinfo=tz).replace(
        hour=hour, minute=minute
    )
    if candidate <= local:
        # Шаг по date, а не +timedelta(hours=24): иначе перевод часов сдвигает
        # расписание навсегда.
        candidate = datetime.combine(local.date() + timedelta(days=1),
                                     datetime.min.time(), tzinfo=tz).replace(
            hour=hour, minute=minute
        )
    return candidate
```

Внутрь процесса время кладут **aware и в UTC**, локальную зону применяют только на выводе (`dt.astimezone(ZoneInfo("Europe/Berlin"))`). Моменты в «недостающий» час перевода (его не было) при конструировании с `tzinfo=` сдвигаются вперёд молча — если такой ввод возможен от пользователя, проверяйте `dt.astimezone(tz) != dt`.

## Отчёт: Counter, Decimal-суммы и защита от CSV-инъекции

```python
"""Сводка по измерениям и запись отчёта."""
import csv
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

def top_by(
    rows: list[dict[str, Any]], key: str, amount: str, n: int = 10
) -> list[tuple[str, Decimal, int]]:
    counts: Counter[str] = Counter()
    totals: dict[str, Decimal] = {}
    for row in rows:
        # Ключ нормализуют до группировки: «Иван » и «Иван» — один человек.
        name = str(row.get(key, "")).strip()
        counts[name] += 1
        # sum(списка_из_Decimal) без start складывает с 0 (int) и падает
        # TypeError на первом значении; sum(..., 0.0) так же тихо роняет точность.
        totals[name] = totals.get(name, Decimal("0")) + Decimal(str(row[amount]))

    # Отчёт читают глазами: по убыванию суммы, число строк вторым столбцом —
    # чтобы «мало строк, большая сумма» было видно сразу.
    ordered = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    return [(name, total, counts[name]) for name, total in ordered[:n]]


def write_report(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    # newline="" — снова обязателен: иначе csv пишет двойные \r\n.
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: safe_cell(v) for k, v in row.items()})

def safe_cell(value: object) -> str:
    """Значение, которое Excel не выполнит.

    Ячейки, начинающиеся с =, +, -, @, формула разбирает как формулу: выгрузка,
    в которую попал пользовательский ввод («=HYPERLINK(...)»), превращается в
    CSV-инъекцию. Апостроф в начале — способ, который Excel показывает как текст.
    """
    text = str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text
```

## Ловушки

- `open(path)` без `newline=""` для csv — на Windows значения с переносом внутри кавычек разъезжаются, а на Linux ошибка приходит позже, в Excel.
- `float` для денег: `0.1 + 0.2 = 0.30000000000000004`. `Decimal` — только из строки: `Decimal(0.1)` тащит двоичный мусор целиком.
- `sum(списка_из_Decimal)` — TypeError (складывать начинает с `int`), а `sum(..., 0.0)` тихо превращает деньги в float. Нужен `Decimal("0")` в start.
- `datetime.strptime(value, "%Y-%m-%d")` отдаёт naive время и в цикле на миллионах строк медленнее `fromisoformat` в разы.
- `datetime.now()` (naive) рядом с `datetime.now(timezone.utc)` — ошибка в сравнении, а в БД такие значения пишутся в неизвестной зоне и расходятся на час после перевода часов.
- Прибавлять `timedelta(hours=24)` к «ежедневному» запуску — терять/ловить час дважды в год. Шаг по `date`, зона — на месте.
- `DictReader` держит в памяти текущую строку, а вот `list(reader)` — весь файл: итоги по дням считаются потоково, без загрузки целиком.
- Формат даты в выгрузке меняется без предупреждения (`2026-1-5` против `2026-01-05`): `fromisoformat` в 3.11+ принимает и так, и так, а `strptime` с `%m-%d` — нет.
- Чужой CSV — это чужой ввод: `=`, `+`, `-`, `@` в начале ячейки и очень длинные поля (`csv.field_size_limit`) относятся к разбору так же, как к выгрузке.

## Related

- [../decisions.md](../decisions.md) — когда stdlib тесно: pandas, openpyxl, polars и цена зависимости
- [json.md](json.md) — схема строк выгрузки: pydantic там, где «битая строка» должна быть ошибкой валидации, а не пропуском
- [testing.md](testing.md) — `tmp_path` и маленький CSV-фикстур: разбор проверяется на файле, а не на строке
- [../../shared/time-and-dates.md](../../shared/time-and-dates.md) — время через границу языков: UTC в хранилище,локальная зона на выводе, арифметика по календарю
- [../../database/snippets/postgres-core.md](../../database/snippets/postgres-core.md) — агрегаты на миллионах строк переезжают в СУБД, где виден план запроса
