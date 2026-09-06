---
id: unity-android-build
title: Android Build: IL2CPP, AAB, ProGuard
lang: unity
min_version: "6.3"
category: snippet
tags: [android, il2cpp, aab, proguard, build]
status: stable
updated: 2026-09-06
---

# Android Build (Unity)

Настройки и проверочный код для Android-сборки: IL2CPP, AAB, target API,
условная компиляция, ProGuard.

**Когда использовать** — любая Android-сборка.
**Когда НЕ использовать** — n/a: это чек-лист + код для Android-таргета.

## Чек-лист сборки

| Параметр | Значение | Почему |
|---|---|---|
| Scripting Backend | **IL2CPP** | производительность, требования Play; Mono — только debug |
| Format | **AAB** (Google Play) | APK — только sideloading/тесты |
| Target API Level | актуальный (требование Play) | старые API — отклонение в Play |
| Min SDK | по аудитории (обычно 24+) | ниже — меньше устройств |
| Architecture | ARM64 (+ ARMv7 по аудитории) | ARM64 — требование для новых приложений |
| Internet Permission | `true`, если есть сеть | иначе `AndroidManifest` без INTERNET |
| ProGuard/R8 | правила для сериализации | рефлексия ломается без правил |

## Код

```csharp
using UnityEngine;
using UnityEngine.Android;

public sealed class AndroidDiagnostics : MonoBehaviour
{
    private void Awake()
    {
#if UNITY_ANDROID
        // API level: адаптация фич (например, 12+ — новые разрешения).
        Debug.Log($"Android API level: {Application.androidApiLevel}");

        // Память: на低端 — снижаем качество.
        var mem = SystemInfo.systemMemorySize; // MB
        if (mem < 4096)
        {
            QualitySettings.SetQualityLevel(0);
            Debug.Log("Low memory device: quality reduced");
        }

        // Разрешения (Android 6+): запрашиваем до использования.
        // Пример: WRITE_EXTERNAL_STORAGE (если нужен).
        var status = Permission.HasUserAuthorizedPermission(Permission.Internet);
        Debug.Log($"INTERNET permission: {status}");
#else
        Debug.Log("Not Android");
#endif
    }
}
```

## ProGuard/R8

При IL2CPP + рефлексии (System.Text.Json, Newtonsoft, сериализация) —
добавьте правила в `Plugins/Android/proguard-user.txt`:

```
# Пример: сохранение типов для сериализации JSON
-keep class com.unity3d.player.** { *; }
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}
```

Проверка: соберите release, запустите сериализацию/рефлексию — если `NoSuchMethodError`/
`ClassNotFoundException` — правила неполные.

## Android-специфичные ловушки

- ❌ `Thread.Sleep`/блокирующие вызовы в main-корутинах — ANR (Application Not Responding).
- ❌ Тяжёлая инициализация в `Awake` первой сцены — долгий старт (splash-screen + async).
- ✅ `Application.lowMemory` — подписка на low-memory callback (освобождать кэши).
- ✅ Thermal: `SystemInfo` + мониторинг температуры (Android API 31+ `ThermalStatus`).
- ✅ Тестировать: старт с холодного состояния, переключение ориентации, background/foreground.

## Related

- [decisions.md — Android](../decisions.md)
- [rules.md — Android](../rules.md)
