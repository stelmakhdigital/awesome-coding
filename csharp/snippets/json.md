---
id: csharp-json
title: "JSON: System.Text.Json + source generation"
lang: csharp
min_version: "10"
category: snippet
tags: [json, serialization, system.text.json, source-gen]
status: stable
updated: 2026-09-06
---

# JSON (C#)

**Когда использовать** — сериализация JSON: `System.Text.Json` со **source generation**
(без рефлексии, быстрее, AOT-friendly).
**Когда НЕ использовать** — legacy-код на `Newtonsoft.Json` (не мигрируйте «на лету»).

## Код

```csharp
using System.Text.Json;
using System.Text.Json.Serialization;

// Использование: сериализация/десериализация через source-gen контекст.
var order = new Order
{
    Id = "42",
    Total = 199.90m,
    Status = OrderStatus.Confirmed,
    Items = [new Item { Sku = "SKU-1", Quantity = 2 }],
};

var json = JsonSerializer.Serialize(order, OrderJsonContext.Default.Order);
var back = JsonSerializer.Deserialize(json, OrderJsonContext.Default.Order)
           ?? throw new InvalidOperationException("Failed to deserialize order");
Console.WriteLine($"{back.Id} {back.Total} {back.Status}");

// POCO: required + init — состояние нельзя сломать после создания.
public sealed class Order
{
    public required string Id { get; init; }
    public required decimal Total { get; init; }
    public OrderStatus Status { get; init; }
    public List<Item> Items { get; init; } = [];
}

public sealed class Item
{
    public required string Sku { get; init; }
    public int Quantity { get; init; }
}

public enum OrderStatus { New, Confirmed, Shipped }

// Source generation: контекст знает типы на этапе компиляции.
// [JsonSerializable] — на КЛАССЕ-контексте (триггер генератора);
// partial record — даёт свойство Default.X.
[JsonSourceGenerationOptions(PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase, WriteIndented = true)]
[JsonSerializable(typeof(Order))]
public partial class OrderJsonContext : JsonSerializerContext
{
    public partial record OrderContext(Order Order);
}
```

## Pitfalls

- ❌ `JsonSerializer.Serialize(obj)` без типа/контекста — рефлексия, медленнее, не AOT.
- ✅ `required` + `init` — десериализация без обязательных полей упадёт сразу.
- ✅ `JsonStringEnumConverter` — если enum'ы должны быть строками в JSON.
- ✅ `decimal` для денег (не `double`).
- ✅ `PropertyNameCaseInsensitive = true` — если JSON приходит от внешних систем.

## Related

- [decisions.md — сериализация](../decisions.md)
