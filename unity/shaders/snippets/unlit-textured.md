---
id: unity-shader-unlit
title: "HLSL: Unlit textured (базовый URP-шейдер)"
lang: unity
min_version: "6.3"
category: snippet
tags: [hlsl, shader, urp, unlit, texture]
status: stable
updated: 2026-09-06
---

# Unlit textured (URP)

**Когда использовать** — базовый шейдер: текстура + тинт, без освещения (2D-спрайты, UI-эффекты, стилизованные сцены).
**Когда НЕ использовать** — нужен свет/тени (Lit shader).

## Код

```hlsl
// Assets/Shaders/UnlitTextured.shader
Shader "Game/Unlit Textured"
{
    Properties
    {
        [PerMaterialData] _MainTex ("Texture", 2D) = "white" {}
        [PerMaterialData] _Tint ("Tint", Color) = (1, 1, 1, 1)
    }

    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent" "RenderPipeline"="UniversalPipeline" }

        Pass
        {
            Name "UnlitTextured"
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            // Material-пропсы: ОБЯЗАТЕЛЬНО в CBUFFER (SRP Batcher).
            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST;
                half4  _Tint;
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

            Varyings vert(Attributes input)
            {
                Varyings output;
                output.uv = TransformTUV(input.uv, _MainTex_ST); // UV-трансформация
                output.positionHCS = TransformObjectToHClip(input.positionOS.xyz);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                half4 tex = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, input.uv);
                return tex * _Tint;
            }
            ENDHLSL
        }
    }
}
```

## Правила

1. **`TransformTUV`** — без него UV-трансформации инспектора (Tiling/Offset) не работают.
2. **`CBUFFER_START(UnityPerMaterial)`** — без него SRP Batcher не объединяет draw calls.
3. **`[PerMaterialData]`** — пропсы, которые участвуют в CBUFFER.
4. **`half4`** для цвета — мобильные GPU.

## Related

- [dissolve.md](dissolve.md) — эффект на базе этого
- [../README.md](../README.md)
