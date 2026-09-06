---
id: unity-addressables
title: "Addressables: загрузка динамического контента"
lang: unity
min_version: "6.3"
category: snippet
tags: [addressables, assets, loading, async, content-update]
status: stable
updated: 2026-09-07
---

# Addressables

**Когда использовать** — динамический контент: уровни, скины, локализация, DLC; кэширование и content update без пересборки.
**Когда НЕ использовать** — статичные ассеты, известные на этапе сборки: обычная ссылка/сцена (см. [decisions.md](../decisions.md)).

## Код

```csharp
using System;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.AddressableAssets;
using UnityEngine.ResourceManagement.AsyncOperations;

public sealed class AssetLoader : MonoBehaviour
{
    // Ассет по ключу (Label/Key из Addressable Groups).
    public async Task<Sprite> LoadSpriteAsync(string key)
    {
        var handle = await Addressables.LoadAssetAsync<Sprite>(key).ToTask();
        if (handle.Status != AsyncOperationStatus.Succeeded)
        {
            Addressables.Release(handle);
            throw new Exception($"addressable '{key}' failed: {handle.OperationException?.Message}");
        }

        var sprite = handle.Result;
        Addressables.Release(handle); // ПОСЛЕ использования Result, не до
        return sprite;
    }

    // Сцена: загрузить, активировать, потом отключить старую.
    public async Task LoadSceneAsync(string key, string oldKey)
    {
        var op = Addressables.LoadSceneAsync(key, LoadSceneMode.Single);
        await op.Task;
        if (op.Status != AsyncOperationStatus.Succeeded)
        {
            Addressables.Release(op);
            throw new Exception($"scene '{key}' failed: {op.OperationException?.Message}");
        }
        Addressables.Release(oldKey); // отпустить старую сцену
    }

    // Пакет ассетов (Label): один handle на весь набор.
    public async Task<AsyncOperationHandle<UnityEngine.Object[]>> LoadSetAsync(string label)
    {
        var handle = await Addressables.LoadAssetsAsync<UnityEngine.Object>(label).ToTask();
        if (handle.Status != AsyncOperationStatus.Succeeded)
        {
            Addressables.Release(handle);
            throw new Exception($"label '{label}' failed");
        }
        return handle; // вызывающий обязан Release после использования
    }
}

// Экстеншен: AsyncOperationHandle -> Task (без UniTask).
public static class AddressablesExtensions
{
    public static Task ToTask<T>(this AsyncOperationHandle<T> op)
    {
        var tcs = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        op.Completed += h =>
        {
            if (h.Status == AsyncOperationStatus.Succeeded) tcs.SetResult(true);
            else tcs.SetException(h.OperationException ?? new Exception("addressable failed"));
        };
        return tcs.Task;
    }
}
```

## Правила

1. **Каждый `Load*` — свой `Release`**: handle без Release = утечка (ассет не выгрузится, кэш разрастётся). Паттерн: `try/finally` или `await` + `Release` сразу после чтения `Result`.
2. **Не `Release` до использования `Result`** — ассет выгрузится раньше, чем вы его применили.
3. **Ключи — не хардкод в 50 местах**: константы/ScriptableObject-реестр, иначе ренейм ломает сборку.
4. **Сцены**: загружайте новую до отключения старой (Single-режим), иначе «дыра» на кадр.
5. **Content Update** (live-игры): `Addressables.UpdateMode` + `PlayerSettings` — проверяйте на реальном устройстве, не только в Editor.

## Pitfalls

- `LoadAssetAsync<T>` с неверным `T` — падает в рантайме; тип ключа проверяйте на этапе сборки (Addressable Groups → Validate).
- Загрузка в `Update`/каждый кадр — не кэшируйте handle в поле без `OnDestroy`-Release.
- Android: кэш живёт в `persistentDataPath` — следите за размером (`Addressables.ClearUnusedResourcesCached`).
- `Addressables.IsInitialized` — при ручной инициализации (`InitializeAsync`) проверяйте перед первым запросом.

## Related

- [scene-management.md](scene-management.md)
- [async.md](async.md)
- [patterns/scriptable-data.md](../patterns/scriptable-data.md)
- [decisions.md](../decisions.md)
