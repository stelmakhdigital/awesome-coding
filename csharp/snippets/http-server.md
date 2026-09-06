---
id: csharp-http-server
title: "HTTP server: ASP.NET Core Minimal API (.NET 10)"
lang: csharp
min_version: "10"
category: snippet
tags: [http, aspnet-core, minimal-api, server, validation, openapi]
status: stable
updated: 2026-09-07
---

# HTTP server: ASP.NET Core Minimal API

**Когда использовать** — новый HTTP-сервис на .NET: REST API, health checks, OpenAPI.
**Когда НЕ использовать** — сложная маршрутизация/версионирование API: Controllers (см. [decisions.md](../decisions.md)).

## Код

```csharp
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHealthChecks();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddOpenApi();
builder.Services.AddScoped<ItemService>();

// JSON: camelCase + nulls не сериализуются (System.Text.Json — дефолт).
builder.Services.ConfigureHttpJsonOptions(o =>
{
    o.SerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
    o.SerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
});

var app = builder.Build();

app.UseHttpsRedirection();
app.MapHealthChecks("/healthz");
app.MapOpenApi(); // GET /openapi/v1.json

var items = app.MapGroup("/api/v1/items").WithTags("items");

items.MapGet("", (ItemService svc) => svc.GetAllAsync())
    .WithName("ListItems");

items.MapGet("/{id:long}", async (long id, ItemService svc, CancellationToken ct) =>
{
    var item = await svc.GetByIdAsync(id, ct);
    return item is null ? Results.NotFound() : Results.Ok(item);
})
    .WithName("GetItem");

items.MapPost("", async (CreateItemRequest req, ItemService svc, CancellationToken ct) =>
{
    var errors = new Dictionary<string, string[]>();
    if (string.IsNullOrWhiteSpace(req.Name)) errors["name"] = ["required"];
    if (req.PriceCents < 0) errors["priceCents"] = ["must be >= 0"];
    if (errors.Count > 0) return Results.ValidationProblem(errors);

    var created = await svc.CreateAsync(req, ct);
    return Results.Created($"/api/v1/items/{created.Id}", created);
})
    .WithName("CreateItem");

app.Run();

// DTO: record + primary constructor (C# 14).
record ItemDto(long Id, string Name, long PriceCents);
record CreateItemRequest(string? Name, long PriceCents);

// Сервис: DI + primary constructor (C# 12+), TimeProvider вместо DateTime.Now.
sealed class ItemService(ILogger<ItemService> logger, TimeProvider time)
{
    public Task<List<ItemDto>> GetAllAsync() => Task.FromResult(new List<ItemDto>
    {
        new(1, "Cup", 350),
    });

    public Task<ItemDto?> GetByIdAsync(long id, CancellationToken ct) =>
        Task.FromResult(id == 1 ? new ItemDto(1, "Cup", 350) : null);

    public Task<ItemDto> CreateAsync(CreateItemRequest req, CancellationToken ct)
    {
        logger.LogInformation("creating item {Name} at {Now}", req.Name, time.LocalNow);
        return Task.FromResult(new ItemDto(1, req.Name!, req.PriceCents));
    }
}
```

## Pitfalls

- **`DateTime.Now` — никогда**: внедряйте `TimeProvider` (тестируемость, UTC-дисциплина — см. [decisions.md](../decisions.md)).
- `Results.ValidationProblem` (422) — стандарт для валидации; не возвращайте 400 с произвольным телом.
- `CancellationToken` в параметрах эндпоинта — обязательный: без него запросы не отменяются при разрыве соединения.
- Не храните состояние в замыканиях/статиках — сервисы в DI (`AddScoped` по умолчанию на запрос).
- `MapGet("/{id:long}")` — route-констрейнты раньше, чем ручные `int.TryParse`.
- CORS: `app.UseCors(...)` с ячным списком origin, не `AllowAnyOrigin` + credentials.
- Для горячего JSON-пути — source generation (`JsonSourceGenerationOptions`), не reflection.

## Related

- [http-client.md](http-client.md)
- [async-await.md](async-await.md)
- [logging.md](logging.md)
- [json.md](json.md)
