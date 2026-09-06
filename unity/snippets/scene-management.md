---
id: unity-scene-management
title: "Scene Management: асинхронная загрузка"
lang: unity
min_version: "6.3"
category: snippet
tags: [scenes, loading, async, addressables]
status: stable
updated: 2026-09-06
---

# Scene Management (Unity)

Асинхронная загрузка сцен: `LoadSceneAsync` + `allowSceneActivation`,
прогресс для UI, `DontDestroyOnLoad` для персистентных систем.

**Когда использовать** — переходы между уровнями/меню без фризов.
**Когда НЕ использовать** — синхронная загрузка в `Awake` «для простоты» (фриз кадра).

## Код

```csharp
using System.Collections;
using UnityEngine;
using UnityEngine.SceneManagement;

public sealed class SceneLoader : MonoBehaviour
{
    [SerializeField] private LoadingUI _loadingUI;

    // Асинхронная загрузка с контролем активации.
    public IEnumerator LoadScene(string sceneName)
    {
        var op = SceneManager.LoadSceneAsync(sceneName, LoadSceneMode.Single);
        op.allowSceneActivation = false; // не активировать, пока не догрузим

        while (op.progress < 0.9f)
        {
            _loadingUI.SetProgress(op.progress / 0.9f);
            yield return null;
        }

        // Финальные 10% — активация (может занять время на слабых устройствах).
        _loadingUI.SetProgress(1f);
        op.allowSceneActivation = true;
        while (!op.isDone)
        {
            yield return null;
        }
    }

    // Аддитивная загрузка (оверлеи, под-уровни).
    public IEnumerator LoadAdditive(string sceneName)
    {
        var op = SceneManager.LoadSceneAsync(sceneName, LoadSceneMode.Additive);
        while (!op.isDone)
        {
            yield return null;
        }
    }

    public IEnumerator UnloadAdditive(string sceneName)
    {
        var scene = SceneManager.GetSceneByName(sceneName);
        if (scene.IsValid())
        {
            var op = SceneManager.UnloadSceneAsync(scene);
            while (!op.isDone)
            {
                yield return null;
            }
        }
    }
}

// Персистентная система: живёт между сценами.
public sealed class GameSession : MonoBehaviour
{
    public int Gold { get; set; }

    private void Awake()
    {
        DontDestroyOnLoad(this);
    }
}
```

## Правила

1. **`allowSceneActivation = false`** до 90%: последние 10% — «скачок» на слабых устройствах.
2. **`DontDestroyOnLoad`** — только для сервисов (сессия, звук, аутентификация), не для игровых объектов.
3. **Очистка при смене сцен**: `OnDisable`/события — подписки снимаются (см. idioms).
4. **Addressables** для контента внутри сцены; сцены — через `SceneManager` (или Addressables-загрузку сцен).

## Android-особенности

- Память: на мобильных держать минимум сцен в памяти одновременно.
- `UnloadSceneAsync` для аддитивных сцен — обязательно (иначе утечка памяти).
- Профилируйте загрузку на低端-устройствах (SSD vs eMMC — разная скорость IO).

## Related

- [decisions.md — async](../decisions.md)
- [rules.md](../rules.md)
