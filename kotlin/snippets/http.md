---
id: kotlin-http
title: "Kotlin: Ktor Client (таймауты, отмена, ретраи)"
lang: kotlin
min_version: "2.3"
category: snippet
tags: [http, ktor, client, timeout, retry]
status: stable
updated: 2026-09-06
---

# HTTP-клиент (Ktor)

**Когда использовать** — сетевые запросы (Android/JVM).
**Когда НЕ использовать** — локальные вызовы (не HTTP).

## Код

```kotlin
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.engine.okhttp.*
import io.ktor.client.request.*
import io.ktor.client.statement.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import io.ktor.client.plugins.*
import io.ktor.client.plugins.contentnegotiation.*
import kotlinx.coroutines.delay
import kotlinx.serialization.Serializable

// @Serializable: обязателен для body<T>() с kotlinx-json.
@Serializable
data class Order(val id: String, val total: Int)

// Клиент: один на приложение, с таймаутами и ретраями.
val client = HttpClient(OkHttp) {
    install(ContentNegotiation) { json() }
    install(HttpTimeout) {
        requestTimeoutMillis = 10_000
        connectTimeoutMillis = 5_000
    }
    install(DefaultRequest) {
        header(HttpHeaders.UserAgent, "app/1.0")
    }
}

// suspend: отменяется вместе с корутиной.
suspend fun fetchOrder(id: String): Order {
    val response = client.get("/orders/$id")
    require(response.status.isSuccess()) { "HTTP ${response.status}" }
    return response.body()
}

// Ретрай с backoff (только для идемпотентных GET).
suspend fun fetchWithRetry(id: String, attempts: Int = 3): Order {
    var last: Throwable? = null
    repeat(attempts) { i ->
        try {
            return fetchOrder(id)
        } catch (e: Exception) {
            last = e
            if (i < attempts - 1) {
                delay(200L * (1 shl i)) // 200, 400, 800 мс
            }
        }
    }
    throw last ?: error("unreachable")
}
```

## Правила

1. **Один клиент** на приложение (пул соединений), не «на запрос».
2. **Таймауты — всегда** (request + connect): без них — висящие запросы.
3. **Ретрай — только идемпотентные** (GET); POST — с `Idempotency-Key`.
4. **`response.status.isSuccess()`** — проверка кода, не «поверил, что 200».
5. **Отмена**: корутина отменена → запрос отменён (проверять в UI: `lifecycleScope`).
6. ❌ Блокирующие вызовы в `Dispatchers.Main`.
7. ❌ Секреты в URL/заголовках в логах.

## Related

- [decisions.md — сеть](../decisions.md)
- [shared/api-design.md](../../shared/api-design.md) — контракты
