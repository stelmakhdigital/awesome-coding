---
id: unity-object-pooling
title: "Object Pooling: пул часто создаваемых объектов"
lang: unity
min_version: "6.3"
category: snippet
tags: [performance, pooling, instantiate, gc]
status: stable
updated: 2026-09-06
---

# Object Pooling (Unity)

Пул объектов: вместо `Instantiate`/`Destroy` — `Get`/`Release` (`SetActive`).
Убирает GC-аллокации и задержки на спавн.

**Когда использовать** — пули, частицы-объекты, текст урона, враги в толпе.
**Когда НЕ использовать** — уникальные объекты (игрок, босс), мало спавнов.

## Код

```csharp
using System.Collections.Generic;
using UnityEngine;

// Универсальный пул: активные объекты — SetActive(true/false).
public sealed class ObjectPool : MonoBehaviour
{
    private readonly Queue<GameObject> _free = new();
    private readonly List<GameObject> _all = new();

    public int FreeCount => _free.Count;

    public GameObject Get(Transform parent = null)
    {
        GameObject obj;
        if (_free.Count > 0)
        {
            obj = _free.Dequeue();
        }
        else
        {
            obj = GameObject.Instantiate(_prefab, transform);
            _all.Add(obj);
        }
        obj.transform.SetParent(parent, false);
        obj.SetActive(true);
        return obj;
    }

    public void Release(GameObject obj)
    {
        obj.SetActive(false);
        _free.Enqueue(obj);
    }

    [SerializeField] private GameObject _prefab;
    [SerializeField, Min(1)] private int _prewarm = 8;

    private void Awake()
    {
        // Prewarm: аллокации до старта игры, не в геймплее.
        for (var i = 0; i < _prewarm; i++)
        {
            var obj = GameObject.Instantiate(_prefab, transform);
            obj.SetActive(false);
            _free.Enqueue(obj);
            _all.Add(obj);
        }
    }
}

// Использование: пул на объекте-спавнере.
public sealed class BulletSpawner : MonoBehaviour
{
    [SerializeField] private ObjectPool _bulletPool;

    public void Fire(Vector3 position, Vector3 direction)
    {
        var bullet = _bulletPool.Get(transform);
        bullet.transform.position = position;
        bullet.transform.forward = direction;
        // Bullet сам вызывает _bulletPool.Release(this.gameObject)
        // при выходе за границы (см. OnDisable в компоненте пули).
    }
}
```

## Правила

1. **Prewarm** в `Awake` — аллокации не в геймплее.
2. **Сброс состояния при `Get`**: компонент объекта должен знать, что его «перезапустили»
   (событие/метод `Reset()`), иначе останутся старые данные.
3. **`Release` — надёжно**: вызывайте из `OnDisable` объекта (покрытие всех путей:
   выход за границу, уничтожение, смена сцены).
4. **Разные пулы на разные типы** — не один «универсальный» на всё.

## Антипаттерны

- ❌ Пул, который всё равно `Destroy`'ит объекты (тогда он не пул).
- ❌ Пул без prewarm — первый спавн всё равно аллоцирует.
- ❌ Один пул на 50 типов объектов.

## Related

- [rules.md — производительность](../rules.md)
