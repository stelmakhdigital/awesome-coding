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

// Отмена: Job.cancel() -> CancellationException в точках подвеса.
fun main() {
    val job = scope.launch {
        repeat(1000) {
            delay(10) // точка подвеса: отмена сработает здесь
            println(it)
        }
    }
    delay(50)
    job.cancel() // остановить
    job.join()   // дождаться завершения
}

// Flow: холодный поток событий.
fun orderUpdates(): Flow<Order> = flow {
    while (true) {
        emit(fetchOrder("42"))
        delay(1000)
    }
}

// StateFlow: горячее состояние (UI).
val state = MutableStateFlow(0)
state.collectLatest { value ->
    // UI: обновить (auto-cancel при завершении scope)
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
