---
id: unity-input
title: "Input: New Input System"
lang: unity
min_version: "6.3"
category: snippet
tags: [input, input-system, gamepad, cross-platform]
status: stable
updated: 2026-09-06
---

# Input (Unity)

**New Input System** (`com.unity.inputsystem`): Input Actions + bindings per platform.
Кроссплатформенность: одна схема — клавиатура, геймпад, тач.

**Когда использовать** — любой новый проект (legacy `Input` — только old code).
**Когда НЕ использовать** — legacy-проект на `Input` (миграция — отдельная задача).

## Код

```csharp
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.OnScreen;

// InputActionAsset (.inputactions) создаётся в Editor:
// Window → General → Input Actions. Здесь — ссылки на actions.
[CreateAssetMenu(menuName = "Game/Player Input")]
public sealed class PlayerInput : UnityEngine.InputSystem.InputActionAsset
{
    // Actions из .inputactions: Move, Jump, Look, Fire.
    public InputAction Move => FindAction("Move");
    public InputAction Jump => FindAction("Jump");
}

public sealed class PlayerMover : MonoBehaviour
{
    [SerializeField] private PlayerInput _input;
    [SerializeField] private float _speed = 5f;

    private Rigidbody _rb;
    private Vector2 _move;

    private void Awake()
    {
        _rb = GetComponent<Rigidbody>();
        _input.Enable();
    }

    private void OnDisable()
    {
        // Отключение: без этого события «текут» после Disable.
        _input.Disable();
    }

    // Callback'и из .inputactions (bind в Editor).
    private void OnMove(InputAction<float, InputAction<float, float>> ctx)
    {
        _move = ctx.ReadValue<Vector2>();
    }

    private void OnJump(InputAction<bool> ctx)
    {
        if (ctx.performed)
        {
            _rb.AddForce(Vector3.up * 7f, ForceMode.Impulse);
        }
    }

    private void FixedUpdate()
    {
        // Движение — в FixedUpdate (физика).
        var dir = transform.right * _move.x + transform.forward * _move.y;
        _rb.velocity = dir * _speed + Vector3.up * _rb.velocity.y;
    }
}
```

## Правила

1. **`.inputactions`-ассет** — единый источник схем; bindings per platform в нём.
2. **`Enable`/`Disable`** в `OnEnable`/`OnDisable` — иначе события «текут».
3. **Движение — в `FixedUpdate`** (физика), визуальные повороты — `Update`/`LateUpdate`.
4. **`performed`/`canceled`** — не `isPressed` в цикле (событийная модель).
5. **On-Screen Controls** (`OnScreen`-компоненты) — для тач-интерфейсов.

## Android-особенности

- Геймпады: Android 6+ поддерживает USB/Bluetooth-геймпады из коробки.
- Тач: `TouchScreenPosition`/`PrimaryTouch` bindings; проверять на разных размерах экранов.
- `Application.androidApiLevel` — для адаптации (см. [android-build.md](android-build.md)).

## Related

- [decisions.md — ввод](../decisions.md)
- [rules.md](../rules.md)
