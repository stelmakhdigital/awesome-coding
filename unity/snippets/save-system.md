---
id: unity-save-system
title: Save System: JSON-сохранения
lang: unity
min_version: "6.3"
category: snippet
tags: [save, persistence, json, settings]
status: stable
updated: 2026-09-06
---

# Save System (Unity)

Сохранения игрока: JSON (`System.Text.Json`) в `Application.persistentDataPath`,
атомарная запись (temp → move), версия схемы.

**Когда использовать** — прогресс игрока (инвентарь, позиция, настройки).
**Когда НЕ использовать** — мелкие ключи (звук, язык): `PlayerPrefs`;
контент, известный на этапе сборки: `ScriptableObject`.

## Код

```csharp
using System;
using System.IO;
using System.Text.Json;
using UnityEngine;

// Схема сохранения: versioned, чтобы мигрировать старые сейвы.
public sealed class SaveData
{
    public int Version { get; set; } = 1;
    public string PlayerName { get; set; } = "";
    public int Gold { get; set; }
    public Vector3Data Position { get; set; } = new();
    public InventoryData Inventory { get; set; } = new();
}

// Vector3 не сериализуется System.Text.Json «из коробки» — своя структура.
public sealed class Vector3Data
{
    public float X { get; set; }
    public float Y { get; set; }
    public float Z { get; set; }

    public static Vector3Data From(Vector3 v) => new() { X = v.x, Y = v.y, Z = v.z };
    public Vector3 ToVector3() => new(X, Y, Z);
}

public sealed class InventoryData
{
    public int WeaponId { get; set; }
    public int Potions { get; set; }
}

public sealed class SaveSystem
{
    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true,
    };

    private static string SavePath =>
        Path.Combine(Application.persistentDataPath, "save.json");

    public static void Save(SaveData data)
    {
        // Атомарно: пишем в temp, затем заменяем.
        // Кrash в середине записи не оставляет полусогласованного сейва.
        var tmp = SavePath + ".tmp";
        File.WriteAllText(tmp, JsonSerializer.Serialize(data, JsonOpts));
        if (File.Exists(SavePath))
        {
            File.Delete(SavePath);
        }
        File.Move(tmp, SavePath);
    }

    public static SaveData? Load()
    {
        if (!File.Exists(SavePath))
        {
            return null;
        }
        var json = File.ReadAllText(SavePath);
        var data = JsonSerializer.Deserialize<SaveData>(json, JsonOpts);
        if (data is null || data.Version != 1)
        {
            // Здесь — миграция старых версий (v0 → v1 и т.д.).
            Debug.LogWarning($"Save version {data?.Version}, expected 1");
            return null;
        }
        return data;
    }
}
```

## Правила

1. **Версия схемы** (`Version`): без неё старые сейвы ломают игру после апдейта.
2. **Атомарная запись** (temp → move): crash не портит сейв.
3. **Свои POCO** для Unity-типов (`Vector3Data`): `System.Text.Json` не знает `Vector3`.
4. **`persistentDataPath`** — единственное надёжное место (не `streamingAssets` — только чтение).
5. **Резервная копия** (опционально): `save.json` + `save.json.bak` при каждом сохранении.

## Android-особенности

- `persistentDataPath` на Android — `/data/data/<package>/files` (доступно приложению).
- После обновления пакета данные сохраняются; после удаления — нет.
- Проверяйте права/объём: на старых устройствах хранилище может быть ограничено.

## Related

- [decisions.md — данные](../decisions.md)
- [rules.md — Android](../rules.md)
