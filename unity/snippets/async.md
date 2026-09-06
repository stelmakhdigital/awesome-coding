---
id: unity-async
title: "Async: корутины vs async/await в Unity"
lang: unity
min_version: "6.3"
category: snippet
tags: [async, coroutines, await, task, unittask]
status: stable
updated: 2026-09-07
---

# Async в Unity: корутины vs async/await

**Когда использовать** — корутины для Unity-таймингов (`WaitForSeconds`, `WaitUntil`), `async/await` для IO/сети (UnityWebRequest, Addressables, JSON).
**Когда НЕ использовать** — блокирующие вызовы на главном потоке (`Thread.Sleep`, sync-IO) — никогда.

## Код

```csharp
using System.Collections;
using System.Threading.Tasks;
using UnityEngine;
using UnityEngine.Networking;

public sealed class AssetLoader : MonoBehaviour
{
    // 1) Unity-тайминги — корутина.
    private IEnumerator SpawnDelayed(GameObject prefab, Vector3 pos, float delay)
    {
        // Realtime: не останавливается при Time.timeScale = 0 (пауза).
        yield return new WaitForSecondsRealtime(delay);
        Instantiate(prefab, pos, Quaternion.identity);
    }

    // 2) Сеть/IO — async/await.
    public async Task<string> LoadTextAsync(string url)
    {
        using var req = UnityWebRequest.Get(url);
        var op = req.SendWebRequest();
        while (!op.isDone)
        {
            await Task.Yield(); // уступить кадр, не блокировать поток
        }
        if (req.result != UnityWebRequest.Result.Success)
        {
            throw new System.Exception($"load failed: {req.error}");
        }
        return req.downloadHandler.text;
    }

    // 3) Адаптер: дождаться Task из корутины (и получить его исключение).
    private static IEnumerator ToEnumerator(Task task)
    {
        yield return new WaitUntil(() => task.IsCompleted);
        task.GetAwaiter().GetResult();
    }

    private IEnumerator LoadAndApply(string url)
    {
        var task = LoadTextAsync(url);
        yield return ToEnumerator(task);
        Debug.Log(task.Result);
    }
}
```

## Правила

1. **Корутины — только для Unity-таймингов** (`WaitForSeconds`, `WaitUntil`, `WaitForEndOfFrame`). Сеть/IO — `async/await`.
2. **`async void` — запрещён**: исключения теряются (Unity пишет в консоль, обработать нельзя). Пишите `async Task` + `try/catch`; fire-and-forget — только с перехватом.
3. **Никаких блокирующих вызовов** на главном потоке: `Thread.Sleep`, sync-файловые IO, `Task.Wait()`/`.Result` — фризы кадра.
4. **`WaitForSeconds` vs `WaitForSecondsRealtime`**: первый останавливается при `Time.timeScale = 0` (пауза/смерть), второй — нет. Осознанный выбор.
5. **`Task.Yield`** в Unity-async = «дождаться следующего кадра» (аналог `yield return null`).

## Pitfalls

- Забытый `await` — задача не запустится (или запустится без ожидания результата).
- Корутина, запущенная `StartCoroutine`, умирает вместе с GameObject — не держите в ней «долгие» состояния.
- `WaitUntil` с тяжёлой проверкой — вызывается каждый кадр; проверка должна быть дешёвой.
- `UnityWebRequest` — не забудьте `using`/`Dispose` (утечка памяти на каждый запрос).
- Гонки: два `async`-метода меняют одно состояние — синхронизируйте (обычно достаточно «всё на главном потоке», но при `Task.Run` — нет).

## Alternatives

- **UniTask** (`com.cysharp.unitask`) — zero-allocation async, `UniTask.WaitForSeconds`, `AwaitableProxy` для корутин. Для горячих путей (тысячи задач/кадр).
- **Addressables** — загрузка ассетов с прогрессом и кэшем (`Addressables.LoadAssetAsync<T>`).

## Related

- [scene-management.md](scene-management.md)
- [state-machine.md](state-machine.md)
- [decisions.md](../decisions.md)
