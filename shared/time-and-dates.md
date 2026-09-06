---
id: shared-time-dates
title: "Shared: Time and dates (кросс-языковые принципы)"
lang: shared
min_version: null
category: concept
tags: [time, dates, timezone, utc, duration]
status: stable
updated: 2026-09-06
---

# Time and dates — принципы

**Когда использовать** — любая работа с датами/временем (хранение, сравнение, отображение).
**Когда НЕ использовать** — n/a: базовая запись.

## Принципы

1. **Храните в UTC** (timestamp), отображайте в локальной зоне пользователя.
2. **Зона — IANA** (`Europe/Moscow`), не offset (`+03:00`) — offset не знает DST.
3. **Разделяйте понятия**:
   - **timestamp** — момент времени (UTC);
   - **date** — календарный день (в зоне!);
   - **duration** — длительность (не зависит от зоны).
4. **Никаких «наивных» datetime** без зоны: `2026-09-06 15:00` — в какой зоне?
5. **Сравнивайте моменты**, а не строки дат; для «календарных» сравнений — в зоне.
6. **Время — инжект** (`TimeProvider`/`clock`), не «сейчас» внутри логики: тестируемость.

## ✅ / ❌

- ✅ `2026-09-06T12:00:00Z` (UTC) в БД/API
- ❌ `2026-09-06 15:00` без зоны
- ✅ `zoneinfo.ZoneInfo("Europe/Moscow")` (Python), `time.LoadLocation` (Go)
- ❌ Фиксированный offset «+3 часа»
- ✅ Длительность: `30 * time.Minute`, не «1800 секунд» магическим числом
- ❌ Арифметика над датами как над числами (переходы месяцев/лет)
- ✅ `TimeProvider`/инжект времени в тестах
- ❌ `time.Now()`/`new Date()`/`datetime.now()` глубоко в бизнес-логике

## По языкам

| Язык | Типы | Зоны |
|---|---|---|
| Go | `time.Time` (всегда с зоной) | `time.LoadLocation`, `time.FixedZone` |
| C# | `DateTimeOffset` (не `DateTime` без `Kind`) | `TimeZoneInfo`, `TimeProvider` |
| Python | `datetime` (aware!) | `zoneinfo` (stdlib 3.9+) |
| TS/JS | `Date` (мс от epoch, UTC внутри) | `Intl.DateTimeFormat`, `date-fns-tz` |
| Kotlin | `java.time` (`Instant`, `ZonedDateTime`) | `ZoneId` |
| C | `time_t` + `struct tm` | `localtime_r`/`gmtime_r` (thread-safe) |

## Related

- [testing.md](testing.md) — фиксированное время в тестах
- [configuration.md](configuration.md) — зона по умолчанию в конфиге
