---
id: kotlin-compose
title: "Kotlin: Jetpack Compose (базовые паттерны)"
lang: kotlin
min_version: "2.3"
category: snippet
tags: [compose, ui, state, viewmodel, android]
status: stable
updated: 2026-09-06
---

# Jetpack Compose (Kotlin)

**Когда использовать** — новый Android-UI.
**Когда НЕ использовать** — legacy Views (пока не мигрировано).

## Код

```kotlin
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

// ViewModel: состояние — StateFlow (не var).
class OrderViewModel : ViewModel() {
    private val _state = MutableStateFlow(OrderUiState())
    val state: StateFlow<OrderUiState> = _state

    fun confirm(id: String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            // suspend-вызов (Ktor/репозиторий)
            // val result = repo.confirm(id)
            _state.value = _state.value.copy(loading = false)
        }
    }
}

data class OrderUiState(
    val loading: Boolean = false,
    val message: String? = null,
)

// Composable: декларативный UI, state-driven.
@Composable
fun OrderScreen(viewModel: OrderViewModel = OrderViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Column {
        Text("Order status: ${state.message ?: "—"}")
        if (state.loading) {
            CircularProgressIndicator()
        } else {
            Button(onClick = { viewModel.confirm("42") }) {
                Text("Confirm")
            }
        }
    }
}
```

## Правила

1. **State-driven**: UI = f(state); мутации — только через ViewModel/State.
2. **`@Stable`/`@Immutable`** для классов состояния (меньше перерисовок).
3. **`remember`/`rememberSaveable`** для локального состояния (не в ViewModel).
4. **`collectAsStateWithLifecycle`** — не собирать Flow, когда UI неактивен.
5. **Композиция**: маленькие @Composable (не один на экран).
6. ❌ Мутация состояния внутри `@Composable` (только через callback/ViewModel).
7. ❌ Сложная логика в @Composable (только рендер + вызовы).

## Related

- [decisions.md — UI](../decisions.md)
- [coroutines.md](coroutines.md) — viewModelScope
