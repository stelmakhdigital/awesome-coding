---
id: csharp-testing
title: "Testing: xUnit, Theory/InlineData"
lang: csharp
min_version: "10"
category: snippet
tags: [testing, xunit, unit-tests, theory]
status: stable
updated: 2026-09-06
---

# Testing (C#)

**Когда использовать** — unit-тесты: `xUnit` (`Fact`, `Theory`, `InlineData`).
**Когда НЕ использовать** — тесты как «страховка» без поведений: тестируйте
инварианты домена, не приватные реализации.

## Код

```csharp
using Xunit;

public sealed class OrderTests
{
    [Fact]
    public void Confirm_TransitionsToConfirmed()
    {
        var order = Order.New("42", 100m);
        order.Confirm();
        Assert.Equal(OrderStatus.Confirmed, order.Status);
    }

    [Theory]
    [InlineData(10_000, 5_000, 5_000)]
    [InlineData(10_000, 10_000, 0)]
    [InlineData(10_000, 15_000, -5_000)]
    public void Balance_AfterWithdrawal(int initialCents, int amountCents, int expectedCents)
    {
        var account = new Account(initialCents);
        account.Withdraw(amountCents);
        Assert.Equal(expectedCents, account.Balance);
    }

    [Fact]
    public void Withdraw_MoreThanBalance_Throws()
    {
        var account = new Account(1_000);
        Assert.Throws<InsufficientFundsException>(() => account.Withdraw(2_000));
    }
}

public enum OrderStatus { New, Confirmed }

public sealed class Order
{
    public string Id { get; }
    public decimal Total { get; }
    public OrderStatus Status { get; private set; }

    private Order(string id, decimal total)
    {
        Id = id;
        Total = total;
        Status = OrderStatus.New;
    }

    public static Order New(string id, decimal total) => new(id, total);

    public void Confirm()
    {
        if (Status is not OrderStatus.New)
        {
            throw new InvalidOperationException($"Cannot confirm order in status {Status}");
        }
        Status = OrderStatus.Confirmed;
    }
}

public sealed class InsufficientFundsException : InvalidOperationException
{
    public InsufficientFundsException() : base("Insufficient funds")
    {
    }
}

public sealed class Account
{
    public int Balance { get; private set; } // в центах

    public Account(int balance) => Balance = balance;

    public void Withdraw(int amount)
    {
        if (amount > Balance)
        {
            throw new InsufficientFundsException();
        }
        Balance -= amount;
    }
}
```

## Правила

- ✅ Имя теста: `Метод_Условие_Ожидание` (`Confirm_TransitionsToConfirmed`).
- ✅ `Theory` + `InlineData` — табличные случаи вместо копипасты `Fact`.
- ✅ AAA: Arrange / Act / Assert — с комментариями при неочевидности.
- ✅ Тестируйте публичный API и инварианты, не приватные детали.
- ❌ Тесты, зависящие от порядка/времени/сети — изолируйте (`TimeProvider`, фейки).
- ⚠️ **`decimal` нельзя в аргументах атрибутов** (`InlineData`) — ограничение C#:
  используйте `int` (центы) или `MemberData` с методом-источником.

## Related

- [decisions.md — тесты](../decisions.md)
