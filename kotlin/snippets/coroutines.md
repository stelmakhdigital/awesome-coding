---
id: kotlin-coroutines
title: "Kotlin: корутины, Flow, отмена"
lang: kotlin
min_version: "2.3"
category: snippet
tags: [coroutines, flow, suspend, cancellation, scope]
status: stable
updated: 2026-09-06
---

# Корутины (Kotlin)

**Когда использовать** — любая асинхронная работа (сеть, БД, UI-обновления).
**Когда НЕ использовать** — CPU-задачи без параллелизма (просто вызов).

## Код

```kotlin
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*

data class Order(val id: String, val total: Int)

// Scope: явный жизненный цикл (не GlobalScope).
val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

// suspend-функция: отменяема, без callbacks.
suspend fun fetchOrder(id: String): Order {
    return withContext(Dispatchers.IO) {
        // имитация IO
        delay(100)
        Order(id, 100)
    }
}

// Параллелизм: async + awaitAll (не последовательно).
suspend fun fetchAll(ids: List<String>): List<Order> {
    return coroutineScope {
        ids.map { id -> async { fetchOrder(id) } }.awaitAll()
    }
}

// Flow: холодный поток событий.
fun orderUpdates(): Flow<Order> = flow {
    while (true) {
        emit(fetchOrder("42"))
        delay(1000)
    }
}

// Отмена: Job.cancel() -> CancellationException в точках подвеса.
fun main() = runBlocking {
    val job = scope.launch {
        repeat(1000) {
            delay(10) // точка подвеса: отмена сработает здесь
            println(it)
        }
    }
    delay(50)
    job.cancel() // остановить
    job.join()   // дождаться завершения

    // Параллелизм: 3 заказа ~ за 100 мс, а не 300.
    val t0 = System.currentTimeMillis()
    val orders = fetchAll(listOf("1", "2", "3"))
    println("orders=${orders.size} time=${System.currentTimeMillis() - t0}ms")

    // Flow в действии: take(2), чтобы не зациклиться.
    val first = orderUpdates().take(2).toList()
    println("flow: ${first.size}")

    // StateFlow: горячее состояние (UI).
    val state = MutableStateFlow(0)
    val collector = launch { state.collectLatest { value -> println("state=$value") } }
    state.emit(1)
    delay(50)
    collector.cancel()
}
```

## Правила

1. **Scope — явный**: `viewModelScope`/`lifecycleScope` (Android) или `CoroutineScope(SupervisorJob() + dispatcher)`.
2. **`SupervisorJob`** для родительских scope (один упавший child не убивает всех).
3. **`withContext`** для смены диспетчера (не `launch` «для переключения»).
4. **`coroutineScope`** для параллелизма: дочерние job'ы завершаются до родителя.
5. **Отмена — кооперативная**: `delay`/`suspend`-функции проверяют; блокирующий код — не отменяется.
6. ❌ `GlobalScope` — «забытый» scope без отмены.
7. ❌ `Thread.sleep` в `Dispatchers.Main` — ANR.

## Related

- [rules.md — корутины](../rules.md)
- [shared/concurrency.md](../../shared/concurrency.md) — принципы
