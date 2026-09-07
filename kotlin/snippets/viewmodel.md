---
id: kotlin-viewmodel
title: "Kotlin: ViewModel + StateFlow + SavedStateHandle (состояние UI)"
lang: kotlin
min_version: "2.3"
category: snippet
tags: [android, viewmodel, stateflow, savedstatehandle, lifecycle, ui-state]
status: stable
updated: 2026-09-07
---

# ViewModel + StateFlow (состояние UI)

**Когда использовать** — состояние экрана на Android: данные для UI, которые должны
пережить вращение/конфигурационные изменения и управляться по lifecycle.
**Когда НЕ использовать** — состояние одного виджета (Compose `remember`);
глобальное состояние приложения (DI-объект/репозиторий).

## Код

```kotlin
// Состояние экрана — immutable data class (одна точка правды).
data class OrderListUiState(
    val orders: List<Order> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
)

class OrderListViewModel(
    private val repo: OrderRepository,
    savedState: SavedStateHandle,
) : ViewModel() {

    // Селекционный параметр — переживает конфигурационные изменения.
    private val customerId: String = savedState["customerId"].orEmpty()

    // StateFlow: горячий поток состояния, последний value — для новых коллекторов.
    private val _uiState = MutableStateFlow(OrderListUiState())
    val uiState: StateFlow<OrderListUiState> = _uiState.asStateFlow()

    init {
        // viewModelScope: отмена при onCleared автоматически.
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }
            runCatching { repo.orders(customerId) }
                .onSuccess { orders ->
                    _uiState.update { it.copy(orders = orders, isLoading = false, error = null) }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isLoading = false, error = e.message ?: "unknown error")
                    }
                }
        }
    }

    // Пользовательское действие: мутация состояния через update (атомарно).
    fun onRetry() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            runCatching { repo.orders(customerId) }
                .onSuccess { _uiState.update { it.copy(orders = it, isLoading = false) } }
                .onFailure { e -> _uiState.update { it.copy(isLoading = false, error = e.message) } }
        }
    }
}
```

Подписка в Compose (см. [compose.md](compose.md)):

```kotlin
@Composable
fun OrderListScreen(viewModel: OrderListViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle() // пауза при background
    when {
        state.isLoading -> Loading()
        state.error != null -> ErrorView(state.error) { viewModel.onRetry() }
        else -> OrderList(state.orders)
    }
}
```

## Правила

1. **Один `UiState`-data class на экран** (не 10 отдельных `LiveData`/`StateFlow`).
2. **Immutable**: `data class` + `copy`/`update`; мутация — только `MutableStateFlow.update`.
3. **`viewModelScope`** — не `GlobalScope`, не ручной `CoroutineScope`.
4. **`collectAsStateWithLifecycle()`** — не `collectAsState()`: не тратим CPU в background.
5. **Селекционные параметры — в `SavedStateHandle`** (`savedState["key"]`), не в
   аргументах `ViewModel`-конструктора (потеряются при конфигурационном изменении).
6. **ViewModel не знает про View**: никаких `Context`, `Activity`, `View`-ссылок
   (`Application` — через DI, осознанно).
7. **Ошибки — в состоянии** (`error: String?`), не в исключениях наружу.

## Pitfalls

- **Мутация списка внутри UiState** (`state.orders.add(...)`) — StateFlow не
  уведомит коллекторов (reference не изменился); всегда `copy` с новым списком.
- **Тяжёлая работа в `init` без scope** — блокирует главный тред.
- **`MutableStateFlow` публичный** — внешние мутации мимо ViewModel;
  наружу только `asStateFlow()`.
- **Состояние в `remember` вместо ViewModel** — потеряно при вращении экрана.
- **Несколько экранов делят один ViewModel** — разные экраны, разные ViewModel
   (общее — в репозитории/DI).

## Related

- [coroutines.md](coroutines.md)
- [compose.md](compose.md)
- [room.md](room.md) — `Flow` из Room → UiState
