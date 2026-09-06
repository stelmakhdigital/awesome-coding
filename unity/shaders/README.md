# Unity — HLSL (шейдеры)

Целевая версия: **Unity 6.3 LTS + URP** (HLSL).
Код рецензирован, не компилируется (нужен Unity Editor).

## Структура URP-шейдера

```
Shader "Game/..."
├── Properties          — поля инспектора (Texture2D, Color, Float)
└── SubShader
    └── Pass
        ├── HLSLPROGRAM
        │   ├── #include "Packages/com.unity.render-pipelines.universal/..."
        │   ├── CBUFFER_START(UnityPerMaterial) — shared-материалы
        │   ├── half4 _MainTex_ST — UV-трансформация (обязательно)
        │   ├── half4 frag(Varyings) : SV_Target
        │   └── ENDHLSL
        └── EndPass
```

## Правила

1. **`CBUFFER_START(UnityPerMaterial)`** — все material-пропсы внутри (иначе shared-материалы ломаются на SRP Batcher).
2. **`half` вместо `float`** для цвета/интенсивности (быстрее на мобильных).
3. **SRP Batcher-совместимость**: без `MaterialKeywords`-мутаций в рантайме, CBUFFER обязателен.
4. **Keywords** (`#pragma multi_compile`) — для опциональных фич (прозрачность, dissolve).
5. **Тестировать на低端-устройствах**: fill rate (полноэкранные эффекты) — главный враг мобильных.
6. ❌ `float4` для цвета, когда `half4` достаточно.
7. ❌ Тяжёлые вычисления в vertex shader для мобильных GPU.

## Записи

| Шейдер | Суть | Файл |
|---|---|---|
| Unlit textured | базовый URP-шейдер с текстурой | [snippets/unlit-textured.md](snippets/unlit-textured.md) |
| Dissolve | эффект растворения (спавн/смерть) | [snippets/dissolve.md](snippets/dissolve.md) |
| Vertex animation | волна в вершинках (трава/вода) | [snippets/vertex-animation.md](snippets/vertex-animation.md) |

## Related

- [../README.md](../README.md) — раздел Unity
- [../decisions.md](../decisions.md) — URP vs HDRP
