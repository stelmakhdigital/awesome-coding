# Kotlin

Целевая версия: **Kotlin 2.3** (latest: 2.3.0, Dec 2025); fallback: 2.2.
Целевые платформы: **JVM/Android** (серверные сервисы + нативный Android).

> Код в этом разделе — рецензирован, не компилируется (нет kotlinc в окружении).
> Перед применением сверяйте API с версией библиотек.

## Конвенции

- **Null safety — строго**: `!!` — только с комментарием и причиной.
- **Иммутабельность по умолчанию**: `val`, `List`/`Map` (не `MutableList`).
- **Корутины** для асинхронности (не callbacks, не `Thread`).
- **Jetpack Compose** для нового Android-UI (см. [decisions.md](decisions.md)).
- **Именованные аргументы** для 2+ параметров; `when` вместо `switch`-цепочек.

## Что нового (Kotlin 2.x)

- **2.0**: Kotlin 2.0 compiler (K2), stable `buildConflicts`.
- **2.1**: `data objects`, `when` как выражение улучшен.
- **2.2**: context parameters (experimental), `@SinceKotlin`.
- **2.3**: unused return value checker, explicit backing fields, Java 25 support.

## Структура раздела

- [rules.md](rules.md) — обязательные правила
- [idioms.md](idioms.md) — идиоматичный Kotlin
- [decisions.md](decisions.md) — таблицы решений (Compose, DI, HTTP, БД)
- [snippets/](snippets/README.md) — готовые сниппеты
