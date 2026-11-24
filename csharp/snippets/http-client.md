---
id: csharp-http-client
title: "HTTP client: IHttpClientFactory + resilience pipeline"
lang: csharp
min_version: "10"
category: snippet
tags: [http, client, ihttpclientfactory, resilience, retry, timeout]
status: stable
updated: 2026-11-24
---

# HTTP client: IHttpClientFactory + resilience

**Когда использовать** — вызовы внешних HTTP API из .NET-сервиса: ретраи, таймауты, пул соединений.
**Когда НЕ использовать** — gRPC: `Grpc.Net.Client` (см. [decisions.md](../decisions.md)).

## Код

```csharp
using Microsoft.Extensions.Http.Resilience;
using System.Text.Json;

// Program.cs: named client + resilience pipeline
// (ретраи 5xx/408/429 и сетевых ошибок + circuit breaker — из коробки).
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient("catalog", c =>
{
    c.BaseAddress = new Uri("https://catalog.example.com/api/v1/");
    c.Timeout = TimeSpan.FromSeconds(15); // дефолт на запрос (включая ретраи)
})
.AddStandardResilienceHandler();   // retry + circuit breaker + timeout на транзитные ошибки HTTP

builder.Services.AddSingleton<CatalogClient>();

var app = builder.Build();
app.Run();

// Типизированный клиент: DI + primary constructor (C# 14).
// Общие опции JSON на приложение: один класс вместо разбросанных
// new JsonSerializerOptions. Web-набор — camelCase, числами в строках не тащит.
static class Json
{
    public static JsonSerializerOptions Options { get; } = new(JsonSerializerDefaults.Web);
}

sealed class CatalogClient(IHttpClientFactory factory, ILogger<CatalogClient> logger)
{
    public async Task<ItemDto?> GetItemAsync(long id, CancellationToken ct = default)
    {
        // Новый экземпляр на каждый вызов: handler (пул соединений) общий.
        using var http = factory.CreateClient("catalog");

        // Таймаут на конкретный запрос строже дефолтного client.Timeout.
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(TimeSpan.FromSeconds(10));

        try
        {
            var resp = await http.GetAsync($"items/{id}", cts.Token);
            if (resp.StatusCode == System.Net.HttpStatusCode.NotFound)
            {
                return null;
            }
            resp.EnsureSuccessStatusCode();
            return await resp.Content.ReadFromJsonAsync<ItemDto>(Json.Options, cts.Token);
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            logger.LogWarning("catalog request timed out: item {Id}", id);
            throw;
        }
    }

    public async Task<ItemDto> CreateItemAsync(CreateItemRequest req, CancellationToken ct = default)
    {
        using var http = factory.CreateClient("catalog");
        var resp = await http.PostAsJsonAsync("items", req, ct);
        resp.EnsureSuccessStatusCode();
        return (await resp.Content.ReadFromJsonAsync<ItemDto>(Json.Options, ct))!;
    }
}

record ItemDto(long Id, string Name, long PriceCents);
record CreateItemRequest(string Name, long PriceCents);
```

## Pitfalls

- **`new HttpClient()` на каждый запрос — socket exhaustion** (порт остаётся в TIME_WAIT). Фабрика решает: handler переиспользуется, экземпляр клиента — дешёвый.
- **Один статический `HttpClient` навсегда — тоже плохо**: DNS-записи «закрепляются» в handler'е. Фабрика периодически обновляет handler.
- `client.Timeout` — дефолт и потолок; точный таймаут на запрос — `CancellationToken` (`CancelAfter`/`CreateLinkedTokenSource`).
- Ретраите только идемпотентные запросы: `TransientHttpResilience` ретраит 5xx/408/429 — для POST нужен идемпотентный ключ.
- `OperationCanceledException` ловите отдельно: отмена по таймауту ≠ отмена вызывающим (`ct.IsCancellationRequested`).
- Не сериализуйте `HttpClient`/handler в кэш — только экземпляр клиента.

## Alternatives

- `Polly` напрямую (без `Microsoft.Extensions.Http.Resilience`) — legacy-стек.
- `Refit`/`AutoMapper`-подобные генераторы клиентов — при большом числе эндпоинтов.

## Related

- [http-server.md](http-server.md)
- [error-handling.md](error-handling.md)
- [decisions.md](../decisions.md)
