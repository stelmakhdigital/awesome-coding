---
id: unity-rules
title: Unity Rules
lang: unity
min_version: "6.3"
category: rule-set
tags: [rules, guardrails, performance, lifecycle, android]
status: stable
updated: 2026-09-07
---

# Unity Rules — обязательные guardrails

## Именование (конвенции Unity)

- ✅ Классы (MonoBehaviour, скрипты): `PascalCase` (`PlayerController`).
- ✅ Публичные поля, свойства, методы, константы: `PascalCase` (`MaxHealth`, `Move()`, `MaxRetries`).
- ✅ Приватные поля: префикс `m_` (`m_health`) — конвенция Unity.
- ✅ Prefab'ы, сцены, ассеты: `PascalCase` (`Player.prefab`, `Level1.unity`).
- ❌ Нет венгерской нотации (`strName`, `bFlag`); поиск по имени — см. «Производительность».

## Производительность (кадр)

- ❌ Аллокации в `Update`/`LateUpdate`: `new`, LINQ, конкатенация строк, `GetComponent` в цикле.
- ✅ Кэш ссылок: `GetComponent`/`Find` — в `Awake`/`Start`, результат — в поле.
- ✅ Object pooling для часто создаваемых объектов (пули, эффекты, текст урона).
- ✅ `Update` — минимально; физика — в `FixedUpdate`; визуальные поправки — `LateUpdate`.
- ✅ `SetActive` вместо `Destroy`/`Instantiate` для переиспользуемых объектов.
- ❌ `FindGameObject`/`Find` по имени в рантайме (кроме отладки).

## Жизненный цикл

- ✅ `Awake` — инициализация полей, кэш ссылок (не зависит от других объектов).
- ✅ `Start` — логика, зависящая от других объектов (вызывается после всех Awake).
- ✅ `OnEnable`/`OnDisable` — подписка/отписка от событий.
- ❌ Логика в `OnDestroy` (порядок разрушения объектов не гарантирован).
- ✅ `[RequireComponent(typeof(Rigidbody))]` — явные зависимости.

## Данные и связь

- ✅ `ScriptableObject` для данных (конфиги, таблицы) — не MonoBehaviour «для хранения».
- ✅ `[SerializeField] private` + `[Tooltip]` — инспектор-настройка без публичных полей.
- ✅ События (C# events) для связи компонентов — не прямые ссылки «на всё».
- ✅ `Addressables` для динамического контента; build-in — только критичное.
- ❌ Статические singleton'ы «на всё» (сценарный glue-код); один осознанный service-ок — ок.

## Android

- ✅ **IL2CPP** для release; Mono — только debug-сборки.
- ✅ **AAB** для Google Play; target API level — актуальный.
- ✅ Проверять ProGuard/R8-правила при рефлексии/сериализации (System.Text.Json, Newtonsoft).
- ✅ Тестировать на слабых устройствах (thermal throttling, 30 fps на минимальной конфигурации).
- ❌ Тяжёлые ассеты в main-сцене — грузить асинхронно / через Addressables.

## Async и корутины

- ✅ Корутины — для Unity-таймингов (`WaitForSeconds`, `WaitUntil`); с возможностью отмены.
- ✅ `async/await` (Unity 2023+) — для IO/сети; не блокировать main-поток.
- ❌ Корутина без `StopCoroutine` при `OnDisable` — «зомби»-корутины.
- ✅ `SceneManager.LoadSceneAsync` + `allowSceneActivation` — контроль загрузки.

## Безопасность

- ✅ Секреты не в `ScriptableObject`/prefab'ах — уходят в билд и извлекаются (decompile).
- ✅ Сеть: TLS (`https` в UnityWebRequest), проверка сертификатов; API-ключи — на бэкенде.
- ✅ `Application.OpenURL` — только с проверенным URI (intent-инъекция на Android).
- ✅ Платежи/лицензии — проверяются на сервере, не в клиенте (клиент реверсится).
- ❌ `Debug.Log` секретов в release (логи собираются на устройствах).

## Related

- [idioms.md](idioms.md) — идиомы
- [decisions.md](decisions.md) — выбор технологий
