---
id: unity-physics
title: "Physics: Rigidbody, коллизии, raycast, слои"
lang: unity
min_version: "6.3"
category: snippet
tags: [physics, rigidbody, collision, raycast, layers]
status: stable
updated: 2026-09-07
---

# Physics (3D)

**Когда использовать** — движение тел, коллизии, триггеры, raycast-запросы (земля, прицел, взаимодействие).
**Когда НЕ использовать** — «физика» для UI или мелких объектов без динамики: обычный `Transform`/движение в коде.

## Код

```csharp
using UnityEngine;

public sealed class PlayerController : MonoBehaviour
{
    [SerializeField] private Rigidbody _rb;
    [SerializeField] private float _speed = 5f;
    [SerializeField] private LayerMask _groundMask;
    [SerializeField] private float _groundDistance = 0.2f;

    // Физика — только в FixedUpdate (синхронно с шагом физики).
    private void FixedUpdate()
    {
        if (!IsGrounded())
        {
            return;
        }

        var move = Input.GetAxis("Horizontal") * _speed;
        // MovePosition — корректное движение dynamic-тела (учитывает коллизии).
        _rb.MovePosition(_rb.position + Vector3.right * move * Time.fixedDeltaTime);
    }

    // Raycast «есть ли земля под ногами».
    private bool IsGrounded()
    {
        var origin = transform.position - Vector3.up * 0.1f;
        return Physics.Raycast(origin, Vector3.down, _groundDistance, _groundMask);
    }

    // Коллизия: только для colliders НЕ-triggers, физический отклик есть.
    private void OnCollisionEnter(Collision collision)
    {
        if (collision.relativeVelocity.magnitude > 10f)
        {
            Debug.Log($"hard hit: {collision.gameObject.name}");
        }
    }

    // Триггер: без физического отклика, только событие.
    private void OnTriggerEnter(Collider other)
    {
        if (other.TryGetComponent(out PickupItem pickup))
        {
            pickup.Collect();
        }
    }
}

// Пример raycast с деталями попадания (прицел/взаимодействие).
public sealed class TargetPicker : MonoBehaviour
{
    [SerializeField] private LayerMask _targetMask;
    [SerializeField] private float _maxDistance = 20f;

    public bool TryPickout(Vector3 origin, out Transform target)
    {
        target = null;
        if (Physics.Raycast(origin, transform.forward, out var hit, _maxDistance, _targetMask))
        {
            target = hit.collider.transform;
            return true;
        }
        return false;
    }
}
```

## Правила

1. **Dynamic Rigidbody: не трогать `transform.position` напрямую** — только `MovePosition`/`MoveRotation`/`MoveVelocity` в `FixedUpdate` (иначе физика «рвётся», телепортация сквозь коллизии).
2. **Кинематические тела** — двигайте через `transform` (они не реагируют на физику, но коллидируют).
3. **Collision vs Trigger**: `OnCollisionEnter` — у colliders без `isTrigger`; `OnTriggerEnter` — у triggers (и у colliders с `isTrigger = true`).
4. **Слои, не теги**: физическое взаимодействие настраивается через Layer Collision Matrix (Project Settings → Physics), `CompareTag` в физике — антипаттерн.
5. **Raycast от персонажа** — смещайте origin или исключайте свой слой, иначе луч бьёт в собственный коллайдер.

## Pitfalls

- `FixedUpdate` vs `Update`: физика — в `FixedUpdate`, ввод/анимация — в `Update`; смешивание — дёргание.
- `Physics.autoSyncTransforms = false` + кинематические тела — забудьте про синхронизацию трансформов.
- Спящие тела (`Rigidbody.Sleep`): толчок не «будит» тело без коллизии — `WakeUp()` явно.
- `collider.isTrigger` на динамическом теле — коллизии не считаются, только триггер-события.
- Много raycast'ов в `Update` — кэшируйте `LayerMask` и используйте `Physics.RaycastAll`/`SphereCast` осознанно.

## Related

- [object-pooling.md](object-pooling.md)
- [async.md](async.md)
- [rules.md — производительность](../rules.md)
