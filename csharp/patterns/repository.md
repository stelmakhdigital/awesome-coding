---
id: csharp-repository
title: "C#: Repository"
lang: csharp
min_version: "10"
category: pattern
tags: [pattern, repository, persistence, ef-core]
status: stable
updated: 2026-09-06
---

# Repository (C#)

Коллекция агрегатов: домен работает с интерфейсом, персистентность скрыта.
**Один repository — на один агрегат** (не на таблицу).

**Когда использовать** — DDD-уровень ≥ 1; на уровне 0 допустим прямой доступ
к `DbContext`/Dapper в application-слое.
**Когда НЕ использовать** — сложное чтение (отчёты, поиск): query service / read-side.

## Код

```csharp
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;

// Интерфейс в домене: асинхронный, с CancellationToken.
public interface IOrderRepository
{
    Task<Order?> GetByIdAsync(string id, CancellationToken ct);
    Task SaveAsync(Order order, CancellationToken ct);
    Task DeleteAsync(string id, CancellationToken ct);
}

// Доменная модель: инварианты — в модели.
public sealed class Order
{
    public string Id { get; }
    public List<OrderItem> Items { get; } = [];
    public OrderStatus Status { get; private set; }

    public Order(string id) => Id = id;

    public void Confirm()
    {
        if (Status is not OrderStatus.New)
        {
            throw new InvalidOperationException($"Order {Id}: cannot confirm from {Status}");
        }
        Status = OrderStatus.Confirmed;
    }
}

public sealed class OrderItem
{
    public string Sku { get; }
    public int Quantity { get; }

    public OrderItem(string sku, int quantity)
    {
        Sku = sku;
        Quantity = quantity;
    }
}

public enum OrderStatus { New, Confirmed }

// Реализация: in-memory (для примера и тестов).
// В продакшене — EF Core / Dapper; домен не знает о БД.
public sealed class InMemoryOrderRepository : IOrderRepository
{
    private readonly Dictionary<string, Order> _orders = new();
    private readonly object _gate = new();

    public Task<Order?> GetByIdAsync(string id, CancellationToken ct)
    {
        Order? order;
        lock (_gate)
        {
            _orders.TryGetValue(id, out order);
        }
        return Task.FromResult(order);
    }

    public Task SaveAsync(Order order, CancellationToken ct)
    {
        lock (_gate)
        {
            _orders[order.Id] = order;
        }
        return Task.CompletedTask;
    }

    public Task DeleteAsync(string id, CancellationToken ct)
    {
        lock (_gate)
        {
            _orders.Remove(id);
        }
        return Task.CompletedTask;
    }
}
```

## Правила

1. **Асинхронные методы + `CancellationToken`** — стандарт для .NET-репозиториев.
2. **На агрегат, не на таблицу**: `IOrderRepository` — да, `IOrderItemRepository` — нет.
3. **Возвращает доменные объекты**, не DTO/`Entity` EF-модели (маппинг на границе).
4. **Сложные запросы — не сюда**: отчёты — query service (CQRS).
5. **Транзакции — в application-слое** (`IDbContextTransaction`), не в repository.

## Антипаттерны

- ❌ EF-`DbContext` в доменных классах.
- ❌ Repository на каждую таблицу с SQL-логикой в домене.
- ❌ «Умный» repository, меняющий состояние агрегата.

## Related

- [go/patterns/repository.md](../../go/patterns/repository.md) — Go-вариант
- [architecture/ddd/tactical/repository.md](../../architecture/ddd/tactical/repository.md) — DDD-концепция
