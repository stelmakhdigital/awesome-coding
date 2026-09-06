---
id: unity-scriptable-data
title: "Unity: Scriptable Data (данные через ScriptableObject)"
lang: unity
min_version: "6.3"
category: pattern
tags: [pattern, scriptableobject, data-driven, configuration]
status: stable
updated: 2026-09-06
---

# Scriptable Data (Unity)

Данные — **ScriptableObject-ассеты**, а не поля MonoBehaviour.
Data-driven: геймдизайнер правит ассеты в Editor, код не меняется.

**Когда использовать** — конфиги, таблицы (оружие, враги, предметы), профили.
**Когда НЕ использовать** — данные игрока (сохранения → JSON, см. [save-system](../snippets/save-system.md));
мелкие ключи → `PlayerPrefs`.

## Код

```csharp
using UnityEngine;

// Ассет данных: создаётся в Editor (Create → Game → Weapon Data).
[CreateAssetMenu(menuName = "Game/Weapon Data")]
public sealed class WeaponData : ScriptableObject
{
    public string displayName = "Pistol";
    public int damage = 25;
    public float fireRate = 8f;
    public float projectileSpeed = 30f;
    public GameObject projectilePrefab;
    public AudioClip fireSound;
}

// Таблица: список ассетов — «база данных» игры.
[CreateAssetMenu(menuName = "Game/Weapon Table")]
public sealed class WeaponTable : ScriptableObject
{
    public WeaponData[] weapons;

    public WeaponData Get(int index) => weapons[index];
}

// Компонент ссылается на данные, а не хранит их.
public sealed class Weapon : MonoBehaviour
{
    [SerializeField] private WeaponData _data;

    public int Damage => _data.damage;
    public float FireRate => _data.fireRate;

    private void Awake()
    {
        if (_data == null)
        {
            Debug.LogError($"{name}: WeaponData not assigned");
            enabled = false;
        }
    }
}
```

## Правила

1. **`[CreateAssetMenu]`** — ассеты создаются в Editor, не в рантайме.
2. **Данные иммутабельны в рантайме**: не менять поля ScriptableObject «на лету»
   (ассет общий для всех ссылок).
3. **Валидация в `Awake`**: null-ссылка на данные — ошибка с понятным логом.
4. **Версионирование**: при изменении схемы данных — мигрировать ассеты (скрипт/меню).
5. **Таблицы — отдельные ассеты** (`WeaponTable`), не массивы в каждом компоненте.

## Антипаттерны

- ❌ MonoBehaviour «для хранения данных» (пустой компонент с публичными полями).
- ❌ Изменение ScriptableObject в рантайме (влияет на все сцены/ссылки).
- ❌ Данные в коде (`const int PistolDamage = 25`) — геймдизайнер не может править.

## Related

- [composition.md](composition.md) — поведение отдельно от данных
- [../snippets/save-system.md](../snippets/save-system.md) — данные игрока
- [decisions.md — данные](../decisions.md)
