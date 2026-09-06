---
id: unity-state-machine
title: State Machine: FSM для игровой логики
lang: unity
min_version: "6.3"
category: snippet
tags: [state-machine, fsm, gameplay, npc]
status: stable
updated: 2026-09-06
---

# State Machine (Unity)

FSM: явные состояния и переходы — вместо `if (isAttacking && isMoving)` в `Update`.
Классика для NPC/игрока: Idle, Move, Attack, Dead.

**Когда использовать** — сущность с 3+ режимами поведения (NPC, игрок, босс).
**Когда НЕ использовать** — 2 режима (флаг достаточно); сложные графы с условиями
и параллельными состояниями → `UnityEngine.AI` (Behavior Designer) или DOTS.

## Код

```csharp
using UnityEngine;

// Базовое состояние: жизненный цикл OnEnter/OnUpdate/OnExit.
public abstract class GameState
{
    protected readonly GameEntity Entity;

    protected GameState(GameEntity entity) => Entity = entity;

    public virtual void OnEnter() { }
    public virtual void OnUpdate(float dt) { }
    public virtual void OnExit() { }
}

public sealed class IdleState : GameState
{
    public IdleState(GameEntity e) : base(e) { }

    public override void OnUpdate(float dt)
    {
        if (Entity.HasTarget)
        {
            Entity.ChangeState(new MoveState(Entity));
        }
    }
}

public sealed class MoveState : GameState
{
    public MoveState(GameEntity e) : base(e) { }

    public override void OnUpdate(float dt)
    {
        Entity.MoveTowardTarget(dt);
        if (Entity.InAttackRange)
        {
            Entity.ChangeState(new AttackState(Entity));
        }
    }
}

public sealed class AttackState : GameState
{
    public AttackState(GameEntity e) : base(e) { }

    public override void OnEnter() => Entity.PlayAttackAnimation();

    public override void OnUpdate(float dt)
    {
        // анимация атаки; по завершении — обратно в Idle
        if (Entity.AttackFinished)
        {
            Entity.ChangeState(new IdleState(Entity));
        }
    }
}

// Держатель: одна активная машина на сущность.
public sealed class GameEntity : MonoBehaviour
{
    private GameState _state;

    public bool HasTarget { get; private set; }
    public bool InAttackRange { get; private set; }
    public bool AttackFinished { get; private set; }

    public void Initialize()
    {
        _state = new IdleState(this);
        _state.OnEnter();
    }

    public void ChangeState(GameState next)
    {
        _state.OnExit();
        _state = next;
        _state.OnEnter();
    }

    private void Update()
    {
        _state.OnUpdate(Time.deltaTime);
    }

    // Заглушки для примера.
    public void MoveTowardTarget(float dt) { }
    public void PlayAttackAnimation() { }
}
```

## Правила

1. **Переходы — в состояниях** (`Entity.ChangeState`), не снаружи «наугад».
2. **`OnEnter`/`OnExit`** — настройка/сброс (анимации, коллайдеры, таймеры).
3. **Состояния — данные о поведении**, не «флаги в Update».
4. **Одна машина на сущность**; параллельные подмашины (локомоция + бой) — отдельные FSM.

## Антипаттерны

- ❌ `Update` с 10 вложенными `if` вместо состояний.
- ❌ Состояния, которые не могут завершиться (нет перехода из Attack).
- ❌ Глобальный статический FSM «для всего мира».

## Related

- [csharp/patterns/state-machine.md](../../csharp/patterns/state-machine.md) — C#-вариант (таблица переходов)
- [patterns/composition.md](../patterns/composition.md)
