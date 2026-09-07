---
id: kotlin-rules
title: "Kotlin Rules"
lang: kotlin
min_version: "2.3"
category: rule-set
tags: [rules, guardrails, null-safety, coroutines, immutability]
status: stable
updated: 2026-09-07
---

# Kotlin Rules — обязательные правила

## Null safety

- ✅ `?` + `?.` + `?:` + `let` — обработка null.
- ❌ `!!` — только с комментарием «почему безопасно» (иначе — баг-магнит).
- ✅ Функции возвращают `T?` осознанно (null = «не найдено», не ошибка).
- ✅ `require`/`requireNotNull` для preconditions (не `!!` на входе).

## Иммутабельность

- ✅ `val` по умолчанию; `var` — только когда мутация нужна.
- ✅ `List`/`Map`/`Set` в сигнатурах (не `MutableList`) — не обещаем мутацию.
- ✅ `data class` для DTO/значений (value semantics, `copy`).
- ❌ Мутабельные `var`-поля в публичных классах.

## Именование (Kotlin conventions)

- ✅ Классы, интерфейсы, объекты: `PascalCase` (`UserService`).
- ✅ Функции, свойства, переменные: `camelCase` (`getItem`, `maxRetries`).
- ✅ Константы (top-level, `object`, `companion`): `PascalCase` (`MaxRetries`) — не `UPPER_SNAKE`.
- ✅ Пакеты: lowercase (`com.example.storage`); имя файла = имя основного класса.
- ✅ «Приватное» — просто `private`, без ведущего подчёркивания.
- ❌ Нет венгерской нотации и заумных аббревиатур.

## Корутины

- ✅ `CoroutineScope` с явным `SupervisorJob` + `Dispatchers` (не `GlobalScope`).
- ✅ `viewModelScope`/`lifecycleScope` в Android (автоматическая отмена).
- ✅ `withContext` для смены диспетчера; `async`/`await` для параллелизма.
- ❌ `Thread.sleep`/блокирующие вызовы в `Dispatchers.Main`.
- ✅ `Flow` для потоков событий; `StateFlow` для состояния.
- ❌ `callback hell` — корутины вместо вложенных колбэков.

## Ошибки

- ✅ Исключения — для непредвиденного; `Result`/`null` — для ожидаемого.
- ✅ `try/catch` — на границах (UI, сеть), не «на каждый вызов».
- ❌ Пустой `catch {}`.

## Android

- ✅ Compose для нового UI (см. [decisions.md](decisions.md)).
- ✅ `@Volatile` для shared-состояния между тредями.
- ✅ Тестировать на слабых устройствах (не только флагманы).
- ❌ Работа с UI из background-тредов.

## Безопасность

- ✅ SQL (Exposed/JDBC): параметризованные запросы, не конкатенация.
- ✅ Крипто: `SecureRandom`/`java.security` (не `Random`); хеши — SHA-256+.
- ✅ Android: `network_security_config` (TLS 1.2+, запрет cleartext); `WebView` —
  без `addJavascriptInterface` у публичных активностей.
- ✅ Секреты: не в коде/ресурсах (R8 «обфусцирует», но не шифрует — бинарник реверсится);
  EncryptedSharedPreferences/Keystore.
- ✅ `exported=true`-компоненты — только осознанно, с проверкой `intent`-входа.

## Related

- [idioms.md](idioms.md) — идиомы
- [decisions.md](decisions.md) — выбор библиотек
