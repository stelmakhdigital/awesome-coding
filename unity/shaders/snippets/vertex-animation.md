---
id: unity-shader-vertex-animation
title: "HLSL: Vertex animation (волна)"
lang: unity
min_version: "6.3"
category: snippet
tags: [hlsl, shader, urp, vertex, animation, grass]
status: stable
updated: 2026-09-06
---

# Vertex animation: волна (URP)

**Когда использовать** — трава, вода, «живые» поверхности (дешёвая анимация без скелетов).
**Когда НЕ использовать** — точная физика (это визуальный приём).

## Код

```hlsl
// Assets/Shaders/VertexWave.shader
Shader "Game/Vertex Wave"
{
    Properties
    {
        [PerMaterialData] _MainTex ("Texture", 2D) = "white" {}
        [PerMaterialData] _WaveHeight ("Wave Height", Range(0, 1)) = 0.1
        [PerMaterialData] _WaveSpeed ("Wave Speed", Range(0, 5)) = 1.0
        [PerMaterialData] _WaveFrequency ("Wave Frequency", Range(0.1, 10)) = 2.0
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }

        Pass
        {
            Name "VertexWave"

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST;
                float  _WaveHeight;
                float  _WaveSpeed;
                float  _WaveFrequency;
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
                output.uv = TransformTUV(input.uv, _MainTex_ST);

                // Волна: sin по XZ + время. Высота — по Y.
                float t = _Time.y * _WaveSpeed;
                float wave = sin(input.positionOS.x * _WaveFrequency + t)
                           * cos(input.positionOS.z * _WaveFrequency + t);
                float3 pos = input.positionOS.xyz;
                pos.y += wave * _WaveHeight;

                output.positionHCS = TransformObjectToHClip(pos);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                return SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, input.uv);
            }
            ENDHLSL
        }
    }
}
```

## Правила

1. **`_Time.y`** — встроенная переменная (секунды), не свой таймер.
2. **Амплитуда — по Y** (для травы/воды); для «дышащих» объектов — по нормали.
3. **Частота/скорость — в инспекторе**: художник настраивает без правки кода.
4. **Мобильные**: sin/cos — относительно дёшевы, но на 100k вершин — мерить (ProBuilder-меш с низкими полигонами).
5. ❌ Сложные вычисления в vert (loop'ы, текстуры) — мобильные GPU.

## Related

- [unlit-textured.md](unlit-textured.md) — база
- [../README.md](../README.md)
