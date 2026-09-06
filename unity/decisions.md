---
id: unity-decisions
title: Unity Decisions
lang: unity
min_version: "6.3"
category: decisions
tags: [decisions, urp, input, addressables, android, choices]
status: stable
updated: 2026-09-06
---

# Unity — таблицы решений

## Рендер

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Мобильные + кросс | **URP** | Built-in (legacy) | — |
| High-end (PC/консоли, RT) | HDRP | URP | бюджет на GPU есть |
| 2D | URP 2D / Built-in 2D | — | — |

## Ввод

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Новый проект | **New Input System** (`com.unity.inputsystem`) | legacy `Input` | — |
| Кроссплатформенные схемы | Input Actions + bindings per platform | ручной `#if` | — |
| Геймпад | New Input System (Gamepad profile) | — | — |

## Данные и контент

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Конфиги/таблицы | **ScriptableObject** | JSON в `persistentDataPath` | данные известны на этапе сборки |
| Динамический контент (уровни, скины, локализация) | **Addressables** | AssetBundles (legacy) | — |
| Сохранения игрока | JSON (`System.Text.Json`) в `persistentDataPath` | `PlayerPrefs` (только мелкие ключи) | — |
| Мелкие настройки (звук, язык) | `PlayerPrefs` | — | — |

## Архитектура

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Игровая логика | **Композиция** (маленькие MonoBehaviour) | DOTS/ECS | тысячи объектов/сложный параллелизм |
| Сложные сущности | Композиция + [state machine](snippets/state-machine.md) | наследование MonoBehaviour | — |
| Связь систем | [Event bus](patterns/event-bus.md) / C# events | прямые ссылки | — |
| Служебные системы (аудитория, звук) | один осознанный service (DI-стиль) | статический singleton «на всё» | — |

## Async и сцены

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Тайминги Unity | корутины (`WaitForSeconds`, `WaitUntil`) | `async` | — |
| Сеть/IO | `async/await` (Unity 2023+) | корутины + callbacks | — |
| Загрузка сцен | `LoadSceneAsync` + `allowSceneActivation` | синхронная загрузка | — |

## Android

| Задача | Рекомендация | Альтернатива | Когда |
|---|---|---|---|
| Backend | **IL2CPP** | Mono (только debug) | release всегда IL2CPP |
| Формат дистрибуции | **AAB** (Google Play) | APK (sideloading/тесты) | — |
| Target API | актуальный (требование Play) | — | — |
| Обфускация | R8/ProGuard + правила для сериализации | — | рефлексия/JSON |
| Производительность | профиль на低端-устройстве, thermal budget | только флагманы | — |

## Related

- [rules.md](rules.md)
- [snippets/android-build.md](snippets/android-build.md) — Android-детали
