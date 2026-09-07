# Kotlin — сниппеты

| Сниппет | Суть | Файл |
|---|---|---|
| Coroutines | scope, `suspend`, `Flow`, отмена | [coroutines.md](coroutines.md) |
| Compose | state-driven UI, ViewModel, StateFlow | [compose.md](compose.md) |
| HTTP (Ktor) | таймауты, ретраи, отмена | [http.md](http.md) |
| Room | Entity, DAO, `Flow`, авто-миграции | [room.md](room.md) |
| ViewModel | `StateFlow` + `SavedStateHandle`, состояние UI | [viewmodel.md](viewmodel.md) |
| Testing | `runTest`, виртуальное время, тесты `Flow` | [testing.md](testing.md) |

Статус кода: `coroutines.md` — скомпилирован (kotlinc 2.3.0) и выполнен; `http.md` — скомпилирован
(Ktor 3.5.2 + OkHttp 5.3.2); `compose.md`, `room.md`, `viewmodel.md`, `testing.md` — рецензированы
(нет Android SDK / kotlinc в окружении).
