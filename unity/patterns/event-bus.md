---
id: unity-event-bus
title: Unity: Event Bus (типизированные события)
lang: unity
min_version: "6.3"
category: pattern
tags: [pattern, events, decoupling, messaging]
status: stable
updated: 2026-09-06
---

# Event Bus (Unity)

Типизированный шина событий: системы общаются через события, не зная друг о друге.
Средний вариант между «прямые ссылки» и «полный message bus».

**Когда использовать** — связь систем (UI ↔ игра, звук ↔ события, аналитика ↔ всё).
**Когда НЕ использовать** — связь двух компонентов (C# event достаточно, см. [composition](composition.md));
«событие на каждый вызов» (over-messaging).

## Код

```csharp
using System;
using System.Collections.Generic;

// Типизированное событие: данные в структуре.
public readonly struct PlayerDamagedEvent
{
    public readonly int Amount;
    public readonly Vector3 Position;
    public PlayerDamagedEvent(int amount, Vector3 position)
    {
        Amount = amount;
        Position = position;
    }
}

public readonly struct PlayerDiedEvent;

// Шина: статический, типизированный, без строк-ключей.
public static class GameEventBus
{
    private static readonly Dictionary<Type, Delegate> _handlers = new();

    public static void Subscribe<T>(Action<T> handler) where T : struct
    {
        var type = typeof(T);
        _handlers[type] = Delegate.Combine(_handlers[type], handler);
    }

    public static void Unsubscribe<T>(Action<T> handler) where T : struct
    {
        var type = typeof(T);
        _handlers[type] = Delegate.Remove(_handlers[type], handler);
    }

    public static void Publish<T>(T evt) where T : struct
    {
        if (_handlers.TryGetValue(typeof(T), out var handler))
        {
            ((Action<T>)handler)?.Invoke(evt);
        }
    }

    // Очистка: при смене сцены/закрытии (защита от утечек).
    public static void Clear() => _handlers.Clear();
}

// Использование.
public sealed class DamageHandler : MonoBehaviour
{
    private void OnEnable()
    {
        GameEventBus.Subscribe<PlayerDamagedEvent>(OnDamaged);
    }

    private void OnDisable()
    {
        GameEventBus.Unsubscribe<PlayerDamagedEvent>(OnDamaged);
    }

    private void OnDamaged(PlayerDamagedEvent e)
    {
        // показать урон, звук — не зная, кто пострадал
    }
}
```

## Правила

1. **Типизированные события** (struct'ы), не строки-ключи (`"player_damaged"`).
2. **`Subscribe` в `OnEnable`, `Unsubscribe` в `OnDisable`** — иначе утечки.
3. **`Clear()` при смене сцен** (защита от «зомби»-подписчиков).
4. **События — факты** (`PlayerDamaged`), не команды (`DamagePlayer`).
5. **Не для всего**: связь двух компонентов — C# event (проще, быстрее).

## Антипаттерны

- ❌ Строковые ключи (`bus.On("damage", ...)`) — тайп-сейфность теряется.
- ❌ Шина вместо прямой зависимости для пары объектов.
- ❌ Подписки без отписки — утечки памяти, «призрачные» обработчики.

## Related

- [composition.md](composition.md) — C# events для пары компонентов
- [../idioms.md](../idioms.md) — пример событий
- [architecture/patterns/event-driven.md](../../architecture/patterns/event-driven.md) — event-driven на уровне архитектуры
