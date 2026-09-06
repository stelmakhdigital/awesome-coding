---
id: kotlin-room
title: "Kotlin: Room (Entity, DAO, Flow, миграции)"
lang: kotlin
min_version: "2.3"
category: snippet
tags: [room, database, android, flow, migrations, persistence]
status: stable
updated: 2026-09-07
---

# Room (Android)

**Когда использовать** — локальная БД в Android-приложении: типобезопасные запросы, реактивные `Flow`, авто-миграции.
**Когда НЕ использовать** — мультиплатформенный проект (iOS + Android): SQLDelight (см. [decisions.md](../decisions.md)).

## Код

```kotlin
// Entity: таблица. @PrimaryKey без autoGenerate — id задаёт вызывающий (UUID/epoch).
@Entity(tableName = "items")
data class Item(
    @PrimaryKey val id: Long,
    val name: String,
    val priceCents: Long, // деньги — целые в минимальных единицах
    val createdAt: Long,  // epoch millis, UTC
)

@Dao
interface ItemDao {
    // Flow: реактивный запрос — UI обновляется при каждом изменении таблицы.
    @Query("SELECT * FROM items ORDER BY createdAt DESC")
    fun observeAll(): Flow<List<Item>>

    // suspend: выполняется на фоновом исполнителе Room, не на main.
    @Query("SELECT * FROM items WHERE id = :id")
    suspend fun byId(id: Long): Item?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(item: Item): Long

    @Query("DELETE FROM items WHERE id = :id")
    suspend fun deleteById(id: Long): Int
}

@Database(entities = [Item::class], version = 1, exportSchema = true)
abstract class AppDatabase : RoomDatabase() {
    abstract fun items(): ItemDao

    companion object {
        @Volatile
        private var instance: AppDatabase? = null

        fun get(context: Context): AppDatabase =
            instance ?: synchronized(this) {
                instance ?: Room.databaseBuilder(
                    context.applicationContext, // applicationContext — не держать Activity
                    AppDatabase::class.java,
                    "app.db",
                )
                    // version = 2: авто-миграция Room 2.6+ (схема экспортируется).
                    // .addMigrations(MIGRATION_1_2) — для ручных миграций
                    .build()
                    .also { instance = it }
            }
    }
}

// ViewModel: Flow → StateFlow, запись — в viewModelScope.
class ItemViewModel(
    private val dao: ItemDao,
) : ViewModel() {

    val items: StateFlow<List<Item>> =
        dao.observeAll()
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun add(name: String, priceCents: Long) {
        val now = System.currentTimeMillis()
        viewModelScope.launch {
            dao.upsert(Item(id = now, name = name, priceCents = priceCents, createdAt = now))
        }
    }

    fun remove(id: Long) {
        viewModelScope.launch { dao.deleteById(id) }
    }
}
```

## Правила

1. **`suspend`-методы DAO** — Room сам уводит их в фоновый поток; `Flow` — реактивно, без ручного диспетчера.
2. **`exportSchema = true`** — обязателен: без экспортированных схем авто-миграции не работают.
3. **`Flow` из DAO** — collect-ите с привязкой к жизненному циклу: `lifecycleScope` + `repeatOnLifecycle` (или `collectAsStateWithLifecycle()` в Compose).
4. **Деньги/время** — `Long` (копейки, epoch millis UTC), не `Double`/`Date`.
5. **Синглтон БД** — `context.applicationContext`, один экземпляр на процесс.

## Pitfalls

- `query.first()`/блокирующий вызов в Compose-композиции или `onCreate` — ANR (main thread).
- `OnConflictStrategy.REPLACE` = DELETE + INSERT: триггеры/связи срабатывают; для «обновления» — `ABORT` + явный UPDATE или `upsert` через `@Insert` + `OnConflictStrategy.ROLLBACK`.
- Изменение схемы без миграции — `IllegalStateException` при открытии БД; не «чините» это удалением файла (потеря данных).
- `Flow`-запрос с тяжёлой сортировкой/JOIN — индекс (`@Index`) на сортируемые/фильтруемые колонки.
- Не держите `Context` (Activity) в полях DAO/репозитория — утечка.

## Related

- [coroutines.md](coroutines.md)
- [compose.md](compose.md)
- [decisions.md](../decisions.md)
