---
id: csharp-idioms
title: C# Idioms
lang: csharp
min_version: "10"
category: idioms
tags: [idioms, style, modern-csharp]
status: stable
updated: 2026-09-06
---

# C# Idioms — идиоматичный современный C#

Каждый блок — самодостаточный (компилируется на .NET 10).

## Primary constructor + DI

```csharp
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

public interface IOrderRepository
{
    Task<Order?> GetByIdAsync(string id, CancellationToken ct);
}

public interface IPaymentGateway
{
    Task ChargeAsync(Order order, CancellationToken ct);
}

public sealed class Order
{
    public string Id { get; }
    public decimal Total { get; }
    public OrderStatus Status { get; private set; }

    public Order(string id, decimal total)
    {
        Id = id;
        Total = total;
        Status = OrderStatus.New;
    }

    public void Confirm() => Status = OrderStatus.Confirmed;
}

public enum OrderStatus { New, Confirmed }

// Primary constructor: зависимости — в сигнатуре класса.
public sealed class OrderService(
    IOrderRepository orders,
    IPaymentGateway payments,
    ILogger<OrderService> logger)
{
    public async Task<Order> ConfirmAsync(string id, CancellationToken ct)
    {
        var order = await orders.GetByIdAsync(id, ct)
            ?? throw new InvalidOperationException($"Order {id} not found");
        order.Confirm();
        await payments.ChargeAsync(order, ct);
        logger.LogInformation("Order {OrderId} confirmed", order.Id);
        return order;
    }
}
```

## `field` — backing field без boilerplate (C# 13)

```csharp
public sealed class Customer
{
    public string Name
    {
        get => field;
        set => field = value?.Trim() ?? throw new ArgumentNullException(nameof(value));
    }
}
```

## Record для DTO

```csharp
public enum OrderStatus { New, Confirmed }

public sealed record OrderDto(string Id, string Customer, decimal Total, OrderStatus Status);
```

## Pattern matching и switch-выражения

```csharp
public abstract class Shape
{
}

public sealed class Circle(double radius) : Shape
{
    public double Radius { get; } = radius;
}

public sealed class Square(double side) : Shape
{
    public double Side { get; } = side;
}

public static class Describer
{
    public static string Describe(Shape shape) => shape switch
    {
        Circle { Radius: > 10 } => "большой круг",
        Circle c => $"круг r={c.Radius}",
        Square { Side: var s } => $"квадрат a={s}",
        _ => "неизвестная фигура",
    };
}
```

## Collection expressions и raw strings (C# 12)

```csharp
// Collection expressions (C# 12): нужен тип-приёмник (var не подойдёт).
int[] ids = [1, 2, 3];
var map = new Dictionary<string, int> { ["a"] = 1 };

var sql = """
    SELECT id, name
    FROM orders
    WHERE status = 'confirmed'
    """;
```

## Extension members (C# 14)

```csharp
public enum OrderStatus { New, Confirmed }

public sealed class Order
{
    public OrderStatus Status { get; init; }
}

// Extension block внутри static-класса (без модификора доступа на самом блоке).
public static class OrderExtensions
{
    extension (Order order)
    {
        public bool IsConfirmed => order.Status is OrderStatus.Confirmed;
    }
}
```

## Null-conditional assignment (C# 14)

```csharp
public static class Disk
{
    public static string? LoadFromDisk() => null;
}

public static class Cache
{
    public static string Get()
    {
        string? cache = null;
        cache ??= Disk.LoadFromDisk(); // присвоить, только если null
        return cache;
    }
}
```

## CancellationToken — везде, где долгая операция

```csharp
using System.Threading;
using System.Threading.Tasks;

public static class Queries
{
    public static async Task<int> GetRecentAsync(int take, CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();
        await Task.Delay(1, ct); // имитация IO
        return take;
    }
}
```

## TimeProvider вместо DateTime.Now

```csharp
using System;

public sealed class Invoice(TimeProvider time)
{
    public bool IsOverdue(DateTime due) => time.GetUtcNow() > due;
}
```

## Related

- [rules.md](rules.md) — обязательные правила
- [snippets/](snippets/README.md) — готовые сниппеты
