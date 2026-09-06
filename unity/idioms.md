---
id: unity-idioms
title: Unity Idioms
lang: unity
min_version: "6.3"
category: idioms
tags: [idioms, lifecycle, composition, scriptableobject]
status: stable
updated: 2026-09-06
---

# Unity Idioms — идиоматичный Unity

Код рецензирован, не компилируется (нужен Unity Editor).

## Жизненный цикл и кэш ссылок

```csharp
using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public sealed class PlayerController : MonoBehaviour
{
    [SerializeField] private float _moveSpeed = 5f;
    [SerializeField] private float _jumpHeight = 2f;

    private Rigidbody _rb;
    private Camera _mainCamera;

    // Awake: кэш ссылок, не зависит от других объектов.
    private void Awake()
    {
        _rb = GetComponent<Rigidbody>();
    }

    // Start: можно полагаться на Awake других объектов.
    private void Start()
    {
        _mainCamera = Camera.main;
    }
}
```

## События вместо прямых ссылок

```csharp
using UnityEngine;

public sealed class HealthComponent : MonoBehaviour
{
    public int MaxHealth { get; private set; } = 100;
    public int CurrentHealth { get; private set; }

    // Событие: подписчики не знают, кто ещё слушает.
    public event System.Action<HealthComponent, int>? Damaged;
    public event System.Action<HealthComponent>? Died;

    public void TakeDamage(int amount)
    {
        if (CurrentHealth <= 0) return;
        CurrentHealth = Mathf.Max(0, CurrentHealth - amount);
        Damaged?.Invoke(this, amount);
        if (CurrentHealth == 0)
        {
            Died?.Invoke(this);
        }
    }
}

// Подписка/отписка — в OnEnable/OnDisable.
public sealed class HealthBar : MonoBehaviour
{
    private HealthComponent _health;

    private void OnEnable()
    {
        _health = GetComponent<HealthComponent>();
        _health.Damaged += OnDamaged;
        _health.Died += OnDied;
    }

    private void OnDisable()
    {
        _health.Damaged -= OnDamaged;
        _health.Died -= OnDied;
    }

    private void OnDamaged(HealthComponent h, int amount) { /* обновить UI */ }
    private void OnDied(HealthComponent h) { /* спавнить эффекты */ }
}
```

## ScriptableObject как данные

```csharp
using UnityEngine;

// Данные — отдельный asset, не MonoBehaviour.
[CreateAssetMenu(menuName = "Game/Weapon Data")]
public sealed class WeaponData : ScriptableObject
{
    public string displayName = "Pistol";
    public int damage = 25;
    public float fireRate = 8f;
    public GameObject projectilePrefab;
}

// Использование: компонент ссылается на данные.
public sealed class Weapon : MonoBehaviour
{
    [SerializeField] private WeaponData _data;

    public int Damage => _data.damage;
}
```

## Платформенные условные компиляции

```csharp
using UnityEngine;

public sealed class PlatformTuner : MonoBehaviour
{
    private void Awake()
    {
#if UNITY_ANDROID
        // Android: снижаем качество, включаем IL2CPP-совместимые пути.
        Application.targetFrameRate = 60;
        Debug.Log("Running on Android, API level " + Application.androidApiLevel);
#elif UNITY_STANDALONE
        Application.targetFrameRate = 144;
#endif
    }
}
```

## Корутина с отменой

```csharp
using UnityEngine;

public sealed class Spawner : MonoBehaviour
{
    private Coroutine _spawnLoop;

    private void OnEnable()
    {
        _spawnLoop = StartCoroutine(SpawnLoop());
    }

    private void OnDisable()
    {
        // Отмена: без этого корутина «доживёт» после Disable.
        if (_spawnLoop != null)
        {
            StopCoroutine(_spawnLoop);
        }
    }

    private System.Collections.IEnumerator SpawnLoop()
    {
        while (true)
        {
            // spawn...
            yield return new WaitForSeconds(1f);
        }
    }
}
```

## Related

- [rules.md](rules.md) — обязательные правила
- [patterns/](patterns/README.md) — паттерны
