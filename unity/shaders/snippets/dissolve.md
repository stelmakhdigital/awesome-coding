---
id: unity-shader-dissolve
title: "HLSL: Dissolve (эффект растворения)"
lang: unity
min_version: "6.3"
category: snippet
tags: [hlsl, shader, urp, dissolve, vfx]
status: stable
updated: 2026-09-06
---

# Dissolve (URP)

**Когда использовать** — спавн/смерть объектов, «растворение» (классика VFX).
**Когда НЕ использовать** — постоянный эффект на всех объектах (fill rate на мобильных).

## Код

```hlsl
// Assets/Shaders/Dissolve.shader
Shader "Game/Dissolve"
{
    Properties
    {
        [PerMaterialData] _MainTex ("Texture", 2D) = "white" {}
        [PerMaterialData] _Cutoff ("Dissolve (0=целый, 1=растворён)", Range(0, 1)) = 0
        [PerMaterialData] _EdgeColor ("Edge Color", Color) = (1, 0.5, 0, 1)
        [PerMaterialData] _EdgeWidth ("Edge Width", Range(0, 0.2)) = 0.03
    }

    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" "RenderPipeline"="UniversalPipeline" }

        Pass
        {
            Name "Dissolve"
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite On

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST;
                float  _Cutoff;
                half4  _EdgeColor;
                float  _EdgeWidth;
            CBUFFER_END

            TEXTURE2D(_MainTex);
            SAMPLER(sampler_MainTex);

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 uv         : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionHCS : SV_POSITION;
                float2 uv          : TEXCOORD0;
            };

            // Шум: простая hash-функция (без текстуры шума).
            float Hash21(float2 p)
            {
                p = frac(p * float2(123.34, 456.21));
                p += dot(p, p + 45.32);
                return frac(p.x * p.y);
            }

            Varyings vert(Attributes input)
            {
                Varyings output;
                output.uv = TransformTUV(input.uv, _MainTex_ST);
                output.positionHCS = TransformObjectToHClip(input.positionOS.xyz);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                float noise = Hash21(input.uv * 8.0);
                // Область растворения: noise < cutoff — «съедено».
                float dissolve = noise - _Cutoff;
                // Кромка: узкая полоса у границы растворения.
                float edge = smoothstep(0.0, _EdgeWidth, dissolve);
                // Кромка светится, остальное — текстура.
                half4 color = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, input.uv);
                color.rgb = lerp(_EdgeColor.rgb, color.rgb, edge);
                color.a = saturate(edge * 4.0); // резкий обрыв за кромкой
                // Полностью растворённое — не рисуем.
                clip(dissolve + _EdgeWidth);
                return color;
            }
            ENDHLSL
        }
    }
}
```

## Управление из кода

```csharp
using UnityEngine;

// Анимация: 0 -> 1 за duration секунд.
public sealed class DissolveEffect : MonoBehaviour
{
    [SerializeField] private Material _material;
    [SerializeField] private float _duration = 1f;

    private float _t;

    public void Play()
    {
        _t = 0f;
        enabled = true;
    }

    private void Update()
    {
        _t += Time.deltaTime / _duration;
        _material.SetFloat("_Cutoff", _t);
        if (_t >= 1f)
        {
            // объект растворён: скрыть/уничтожить (через пул — см. object-pooling)
            enabled = false;
            gameObject.SetActive(false);
        }
    }
}
```

## Правила

1. **`clip()`** — не рисовать растворённые пиксели (fill rate).
2. **Шум — по UV** (стабильный), не по world-координатам (мерцание).
3. **Материал — уникальная инстанция** (`material`-копия), не shared (иначе «растворяются» все).
4. **Мобильные**: уменьшать `_EdgeWidth`, шум — дешёвый (без текстур).

## Related

- [unlit-textured.md](unlit-textured.md) — база
- [../../snippets/object-pooling.md](../../snippets/object-pooling.md) — спавн/смерть объектов
