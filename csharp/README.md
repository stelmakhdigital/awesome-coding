# C#

Целевая версия: **.NET 10 (LTS) / C# 14** (закреплено и проверено на 2026-09-06).
Fallback: .NET 9 / C# 13.

.NET 10 — LTS (поддержка 3 года); .NET 11 выйдет в ноябре 2026.

## Конвенции проекта

```xml
<!-- csproj: минимальный набор -->
<PropertyGroup>
  <TargetFramework>net10.0</TargetFramework>
  <Nullable>enable</Nullable>
  <ImplicitUsings>enable</ImplicitUsings>
  <LangVersion>latest</LangVersion>
  <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
</PropertyGroup>
```

- **Nullable reference types — включены**: `string?` осознанно, `null` не «пробрасывается».
- **File-scoped namespaces**: `namespace My.App;`
- **Primary constructors** для классов с DI: `public class Service(ILogger<Service> log) {}`
- **`sealed` по умолчанию**: класс не наследуется, если нет явной причины.
- **Паттерны вместо ладдера типов**: `is`/`switch`-выражения.

## Что нового (не пишите устаревший код)

- **C# 12**: primary constructors, collection expressions `[]`, `using` alias, raw string literals.
- **C# 13**: `field` — синтетический backing field свойства; `required`-поля в `record`.
- **C# 14** (.NET 10): **extension members** (extension-свойства/методы через `extension`-блок),
  **null-conditional assignment** (`?=`), `nameof` для unbound generic types,
  дополнительные неявные конверсии `Span<T>`, модификаторы у параметров простых ламбд,
  `partial` для событий и конструкторов, user-defined compound assignment operators.

## Инструменты

- `dotnet format` (форматирование + фиксы по анализаторам)
- Built-in analyzers: `<EnableNETAnalyzers>true</EnableNETAnalyzers>` + `<AnalysisLevel>latest-recommended</AnalysisLevel>`
- Тесты: xUnit (см. [decisions.md](decisions.md))

## Структура раздела

Все блоки кода в разделе — самодостаточные файлы, **проверены компиляцией на .NET 10 (C# 14)**.

- [rules.md](rules.md) — обязательные guardrails (✅/❌)
- [idioms.md](idioms.md) — идиоматичный C#
- [decisions.md](decisions.md) — таблицы выбора библиотек
- [snippets/](snippets/README.md) — готовые сниппеты
- [patterns/](patterns/README.md) — паттерны
