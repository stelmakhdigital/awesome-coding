---
id: csharp-functional-options
title: "C#: Functional Options (builder)"
lang: csharp
min_version: "10"
category: pattern
tags: [pattern, options, builder, configuration]
status: stable
updated: 2026-09-06
---

# Functional Options (C#)

Конфигурация объекта через builder: явные дефолты, флюентные `With*`-методы,
иммутабельный результат.

**Когда использовать** — объект с несколькими опциональными параметрами (клиенты,
конфигурации, фабрики).
**Когда НЕ использовать** — 1–2 параметра (просто аргументы конструктора);
полная конфигурация из внешнего конфига (Options pattern, `IOptions<T>`).

## Код

```csharp
// Использование: вызов читается как «что отклоняется от дефолтов».
var options = new PaymentGatewayOptionsBuilder()
    .WithEndpoint("https://prod.payments.example.com")
    .WithTimeout(TimeSpan.FromSeconds(10))
    .Build();

// Иммутабельные опции: состояние задаётся один раз.
public sealed class PaymentGatewayOptions
{
    public string Endpoint { get; }
    public TimeSpan Timeout { get; }
    public int MaxRetries { get; }

    internal PaymentGatewayOptions(string endpoint, TimeSpan timeout, int maxRetries)
    {
        Endpoint = endpoint;
        Timeout = timeout;
        MaxRetries = maxRetries;
    }
}

// Builder: валидация на каждом шаге, результат — Build().
public sealed class PaymentGatewayOptionsBuilder
{
    private string _endpoint = "https://payments.example.com";
    private TimeSpan _timeout = TimeSpan.FromSeconds(30);
    private int _maxRetries = 3;

    public PaymentGatewayOptionsBuilder WithEndpoint(string endpoint)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(endpoint);
        _endpoint = endpoint;
        return this;
    }

    public PaymentGatewayOptionsBuilder WithTimeout(TimeSpan timeout)
    {
        // TimeSpan — не числовой тип: ThrowIfNegative не подходит.
        if (timeout < TimeSpan.Zero)
        {
            throw new ArgumentOutOfRangeException(nameof(timeout), timeout, "Timeout must be non-negative");
        }
        _timeout = timeout;
        return this;
    }

    public PaymentGatewayOptionsBuilder WithMaxRetries(int maxRetries)
    {
        ArgumentOutOfRangeException.ThrowIfLessThan(maxRetries, 0);
        _maxRetries = maxRetries;
        return this;
    }

    public PaymentGatewayOptions Build() => new(_endpoint, _timeout, _maxRetries);
}
```

## Правила

1. **Дефолты — в builder'е**, не в вызывающем коде: вызов читается как «что отклоняется».
2. **Валидация в `With*`** — невалидные опции не доходят до `Build()`.
3. **Результат иммутабелен** (`get-only` свойства) — опции можно шарить.
4. **`Build()` — явный финиш**: нет «тихого» использования полуготового объекта.

## Антипаттерны

- ❌ Builder без дефолтов (все `With*` обязательны) — это просто конструктор.
- ❌ Мутабельные опции, которые «ещё докрутят» после `Build()`.
- ❌ 20 `With*`-методов — разбейте на несколько объектов конфигурации.

## Related

- [go/patterns/functional-options.md](../../go/patterns/functional-options.md) — Go-вариант
- [decisions.md — конфигурация](../decisions.md)
