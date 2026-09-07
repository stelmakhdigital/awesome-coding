---
id: kotlin-testing
title: "Kotlin: тестирование корутин (runTest, виртуальное время, Flow)"
lang: kotlin
min_version: "2.3"
category: snippet
tags: [testing, coroutines, runtest, virtual-time, flow, junit]
status: stable
updated: 2026-09-07
---

# Тестирование корутин

**Когда использовать** — любые `suspend`-функции, `Flow`, ViewModel, репозитории.
**Когда НЕ использовать** — тестирование реального времени/таймеров «как есть»
(виртуальное время `runTest` их скрывает — для реальных таймеров — интеграционные тесты).

## Код

```kotlin
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import kotlin.test.*
// JUnit5: import org.junit.jupiter.api.Test

// 1) Базовый: runTest — виртуальное время, delay не ждёт реальных миллисекунд.
@Test
fun fetchOrder_succeeds() = runTest {
    val order = fetchOrder("42") // suspend-функция с delay(100) внутри
    assertEquals("42", order.id)
}

// 2) Таймаут: сбой за 5 секунд виртуальных, тест — мгновенный.
@Test
fun fetchOrder_timesOut() = runTest {
    val result = withTimeoutOrNull(5_000) { fetchOrderSlow() } // delay(10_000) внутри
    assertNull(result)
}

// 3) Ошибки: assertFailsWith вместо «надеюсь, упадёт».
@Test
fun fetchOrder_propagatesError() = runTest {
    assertFailsWith<IOException> { fetchOrder("missing") }
}

// 4) Flow: собираем элементы, проверяем последовательность и завершение.
@Test
fun orderUpdates_emitsInOrder() = runTest {
    val values = orderUpdates().take(3).toList()
    assertEquals(3, values.size)
    assertTrue(values.isSorted())
}

// 5) StateFlow: последнее значение + обновления.
@Test
fun stateFlow_lastValueWins() = runTest {
    val state = MutableStateFlow(0)
    val seen = mutableListOf<Int>()
    val job = launch { state.take(3).toList().also { seen += it } }
    state.emit(1)
    state.emit(2)
    state.emit(3)
    job.join()
    assertEquals(listOf(0, 1, 2, 3), seen) // 0 — начальное, конколенция схлопывается
}

// 6) Отмена: задача отменяется, ресурсы освобождены.
@Test
fun cancelledJob_releasesResource() = runTest {
    var released = false
    val job = launch {
        try { fetchOrder("42") } finally { released = true }
    }
    job.cancel()
    job.join()
    assertTrue(released)
}

// 7) Тест дедлайна: advanceTimeByExplicitly — точный контроль времени.
@Test
fun retryAfterDelay() = runTest {
    val result = withContext(Dispatchers.Default) {
        withTimeout(3_000) {
            delay(1_000)
            "done"
        }
    }
    assertEquals("done", result)
    assertEquals(1_000, currentTime) // виртуальные часы
}
```

## Правила

1. **`runTest` по умолчанию** — не `runBlocking` в тестах (runBlocking не
   управляет виртуальным временем и не ждёт дочерних задач).
2. **`delay` в коде под тестом — ок**: в `runTest` он мгновенный (виртуальное время).
3. **`UnconfinedTestDispatcher`/`StandardTestDispatcher`** — явный выбор:
   Standard (по умолчанию в runTest) — предсказуемый порядок; Unconfined —
   «выполнить сразу» (осторожно, скрывает гонки).
4. **Тестируйте поведение, не реализацию**: результат/состояние, не «вызывался
   метод X» (мок-верификация — только для побочных эффектов).
5. **Flow-тесты**: `take(N)`/`toList()` — конечность; бесконечный Flow без
   ограничения — зависший тест.
6. **Ошибки — `assertFailsWith<T>`** с конкретным типом; не `try/catch + fail()`.
7. **Реальные таймеры/системное время** — вне `runTest`: интеграционный тест
   или инъекция `TimeSource`/`Clock`.

## Android-специфика

- **ViewModel-тесты**: `viewModelScope` использует `Dispatchers.Main.immediate` —
  в юнит-тестах нужен `MainDispatcherRule` (junit4) или
  `Dispatchers.setMain(UnconfinedTestDispatcher())` (junit5, `Dispatchers.resetMain()`
  в `@AfterEach`).
- **Compose-тесты** — отдельный слой (`createComposeRule`), не смешивать с юнитом.
- **Репозитории**: интерфейс + фальш-реализация (in-memory), не реальные сети/БД.

## Pitfalls

- **`runBlocking` в тесте** — реальные задержки + «забытые» дочерние job'ы.
- **Виртуальное время как реальное**: `delay(1000)` в runTest ≠ 1 секунда —
  тесты с реальными таймаутами/ретраями пишутся отдельно.
- **`Dispatchers.Main` без правила** — «Module with the Main dispatcher is missing»
  (Android-юнит-тесты).
- **Тест «проходит» только в одиночку** — общее состояние (singleton, Main
  dispatcher) не очищается между тестами.

## Related

- [coroutines.md](coroutines.md)
- [viewmodel.md](viewmodel.md)
- [shared/testing.md](../../shared/testing.md)
