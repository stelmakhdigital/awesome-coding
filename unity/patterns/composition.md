---
id: unity-composition
title: Unity: Composition (композиция компонентов)
lang: unity
min_version: "6.3"
category: pattern
tags: [pattern, composition, gameobject, design]
status: stable
updated: 2026-09-06
---

# Composition (Unity)

Сущность = **композиция маленьких компонентов**, а не иерархия наследования.
`Enemy` — это не `class Enemy : MonoBehaviour` на 1000 строк,
а GameObject с `HealthComponent` + `EnemyAI` + `EnemyAnimator` + `EnemySpawner`.

**Когда использовать** — всегда: это базовый принцип Unity.
**Когда НЕ использовать** — «универсальный» компонент на всё (anti-composition).

## Код

```csharp
using UnityEngine;

// Маленький компонент: одна ответственность.
public sealed class HealthComponent : MonoBehaviour
{
    [SerializeField] private int _maxHealth = 100;

    public int MaxHealth => _maxHealth;
    public int CurrentHealth { get; private set; }

    public event System.Action<HealthComponent, int>? Damaged;
    public event System.Action<HealthComponent>? Died;

    private void Awake() => CurrentHealth = _maxHealth;

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

// AI подписывается на события, а не знает про «врага».
public sealed class EnemyAI : MonoBehaviour
{
    private HealthComponent _health;

    private void Awake() => _health = GetComponent<HealthComponent>();

    private void OnEnable() => _health.Died += OnDied;
    private void OnDisable() => _health.Died -= OnDied;

    private void OnDied(HealthComponent h)
    {
        // спавнить лут, анимацию смерти — через события/пул
    }
}
```

## Правила

1. **Один компонент — одна ответственность**: `HealthComponent` не знает про AI и анимации.
2. **Связь через события/интерфейсы**, не прямые ссылки «на всё».
3. **`[RequireComponent]`** — явные зависимости между компонентами.
4. **Наследование MonoBehaviour — почти никогда**: полиморфизм через компоненты.
5. **Данные — ScriptableObject** (см. [scriptable-data.md](scriptable-data.md)), не поля компонентов.

## Антипаттерны

- ❌ `class BossEnemy : Enemy, IFlyable, IArmored` — иерархия + интерфейсы на MonoBehaviour.
- ❌ Компонент на 500+ строк — разбить.
- ❌ Прямые ссылки `GetComponent<EnemyAI>()` в каждом компоненте — события.

## Related

- [scriptable-data.md](scriptable-data.md) — данные отдельно от поведения
- [event-bus.md](event-bus.md) — связь систем
- [../idioms.md](../idioms.md)
