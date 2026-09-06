---
id: kotlin-idioms
title: "Kotlin Idioms"
lang: kotlin
min_version: "2.3"
category: idioms
tags: [idioms, style, data-class, sealed, extensions, when]
status: stable
updated: 2026-09-06
---

# Kotlin Idioms — идиоматичный Kotlin

Код рецензирован, не компилируется (нет kotlinc).

## Data class и value semantics

```kotlin
// DTO: data class (equals/hashCode/copy/toString — бесплатно).
data class Order(
    val id: String,
    val total: BigDecimal,
    val status: OrderStatus,
)

enum class OrderStatus { New, Confirmed, Shipped }

// copy — неизменяемое обновление.
val confirmed = order.copy(status = OrderStatus.Confirmed)
```

## Sealed class (замкнутый набор состояний)

```kotlin
// Замкнутая иерархия: when без else — компилятор проверит полноту.
sealed interface Result<out T> {
    data class Success<T>(val value: T) : Result<T>
    data class Failure(val error: String, val code: Int) : Result<Nothing>
}

fun handle(r: Result<Int>) = when (r) {
    is Result.Success -> "got ${r.value}"
    is Result.Failure -> "error ${r.code}: ${r.error}"
    // без else: компилятор знает, что вариантов больше нет
}
```

## Extension functions

```kotlin
// Расширение: без наследования, в scope импорта.
fun String.masked(): String = if (length <= 4) this else take(4) + "****"

fun List<Int>.sumEven(): Int = filter { it % 2 == 0 }.sum()
```

## Scope functions (let/run/also/with/apply)

```kotlin
// let: null-check + действие в одном выражении.
val name = user?.name?.let { it.trim() } ?: "unknown"

// apply: конфигурация объекта (this — контекст).
val config = Config().apply {
    timeout = 30
    retries = 3
}

// also: побочное действие (this — аргумент), возвращает объект.
val file = File("out.txt").also { it.parentFile?.mkdirs() }
```

## when вместо if-цепочек

```kotlin
// when-выражение: возвращает значение, покрывает все ветки.
val label = when (order.status) {
    OrderStatus.New -> "Новый"
    OrderStatus.Confirmed -> "Подтверждён"
    OrderStatus.Shipped -> "Отправлен"
}

// when с условиями.
val discount = when {
    total > 1000 -> 0.2
    total > 500 -> 0.1
    else -> 0.0
}
```

## Null safety на практике

```kotlin
// require: precondition (IllegalArgumentException).
fun parseId(raw: String?): String {
    requireNotNull(raw) { "order id is required" }
    require(raw.isNotBlank()) { "order id must not be blank" }
    return raw
}

// elvis: дефолт для null.
val timeout = config.timeout ?: 30_000
```

## Related

- [rules.md](rules.md) — обязательные правила
- [snippets/coroutines.md](snippets/coroutines.md) — корутины
