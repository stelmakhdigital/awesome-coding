# C# — сниппеты

| Сниппет | Суть | Файл |
|---|---|---|
| Error handling | кастомные исключения, `catch when`, валидация аргументов | [error-handling.md](error-handling.md) |
| Async/await | `Task.WhenAll`, `CancellationToken` | [async-await.md](async-await.md) |
| Collections | List/Dictionary, LINQ vs циклы, Span | [collections.md](collections.md) |
| JSON | `System.Text.Json` + source generation | [json.md](json.md) |
| Logging | `ILogger<T>`, scopes, структурированные сообщения | [logging.md](logging.md) |
| Testing | xUnit: `Fact`, `Theory`, `InlineData` | [testing.md](testing.md) |
| HTTP server | ASP.NET Core Minimal API: DI, валидация, OpenAPI | [http-server.md](http-server.md) |
| HTTP client | `IHttpClientFactory` + resilience (ретраи, таймауты) | [http-client.md](http-client.md) |

Все блоки кода — самодостаточные файлы, компилируемые на .NET 10 (C# 14).
