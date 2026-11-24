# LLM — приложения с моделью

Раздел про код, который вызывает модель: вызов, ответ по схеме, ретраи, бюджет,
кэш, оценка изменения промпта. Не про то, какие модели лучше, и не про обучение.

## Что закреплено

Версию модели закрепить нельзя — она меняется провайдером. Поэтому в разделе
закреплено другое:

- **контракт**: chat-completions-совместимый HTTP (`/chat/completions`, `usage`,
  `choices[].message.content`) — он сходится у провайдеров и у локальных серверов;
- **код раздела**: Go 1.27 (stdlib), Python 3.11+ (`httpx`) — проходят `make verify`;
- **правила**: не зависят от провайдера и от версии модели.

Конкретную модель, её снапшот и цену за токены держите в конфигурации проекта
([../shared/configuration.md](../shared/configuration.md)), а не в коде: прайс
меняется чаще, чем код.

## Структура раздела

- [rules.md](rules.md) — обязательные guardrails (таймауты, ретраи, деньги, промпт, логи)
- [decisions.md](decisions.md) — SDK или HTTP, стриминг, где считать, локальная модель
- [evals.md](evals.md) — как проверять смену промпта и модели
- [snippets/structured-output.md](snippets/structured-output.md) — Go: вызов со схемой и бюджетом
- [snippets/retries-budget.md](snippets/retries-budget.md) — Python: ретраи, бюджет, кэш
- [snippets/streaming.md](snippets/streaming.md) — Go: SSE-стриминг ответа, простои, отмена клиента
- [snippets/tool-calls.md](snippets/tool-calls.md) — Go: вызовы с инструментами, цикл с бюджетом, резервная модель

## Related

- [../shared/security.md](../shared/security.md) — prompt injection — частный случай
  «не доверяй внешнему вводу»
- [../go/snippets/rate-limit.md](../go/snippets/rate-limit.md) — ограничение параллельности
  при массовой обработке
