---
id: go-tracing
title: "Go: OpenTelemetry — трейсер, span'ы, propagate контекста"
lang: go
min_version: "1.22"
category: snippet
tags: [tracing, opentelemetry, otel, observability, context, http]
status: stable
updated: 2026-11-24
---

# OpenTelemetry-трейсинг (Go)

**Когда использовать** — любой сервис с вызовами наружу: HTTP-клиент/сервер, БД,
очереди. Один `traceparent` на цепочке отвечает на «где именно висло 800 мс»,
которого логи не отвечают.
**Когда НЕ использовать** — один процесс без внешних вызовов (трейс из одного
span'а дешевле лога) и там, где уже есть готовый слой instrumentation от
фреймворка — два параллельных трейсинга хуже одного.

## Настройка

```go
// Package tracing — OpenTelemetry: трейсер, span'ы, propagate контекста.
package tracing

import (
	"context"
	"fmt"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

// Init подключает экспорт трейсов по OTLP/HTTP и глобальный propagator.
// Возвращает shutdown: вызывать при остановке процесса, иначе последние батчи
// спанов не уйдут (см. go/snippets/graceful-shutdown.md).
//
// endpoint — «collector:4318», без схемы; service — имя сервиса в бэкенде.
func Init(ctx context.Context, endpoint, service string, ratio float64) (func(context.Context) error, error) {
	exp, err := otlptracehttp.New(ctx,
		otlptracehttp.WithEndpointURL("http://"+endpoint))
	if err != nil {
		return nil, fmt.Errorf("otlp exporter: %w", err)
	}

	// ParentBased: начало трейса у клиента решается нами, продолжение — по
	// родительскому флагу. Иначе трейсы обрываются на границе сервисов: один
	// сервис сэмплирует, второй нет, и картина рваная.
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exp),
		sdktrace.WithSampler(sdktrace.ParentBased(sdktrace.TraceIDRatioBased(ratio))),
		// NewSchemaless: service.name атрибутом, без привязки к версии semconv.
		sdktrace.WithResource(resource.NewSchemaless(attribute.String("service.name", service))),
	)

	otel.SetTracerProvider(tp)
	// Без propagator'а исходящие запросы уходят без traceparent, и трейс
	// обрывается на первом же hop. W3C traceparent — общий знаменатель систем.
	otel.SetTextMapPropagator(propagation.TraceContext{})

	return tp.Shutdown, nil
}

// Span оборачивает работу в span: без End() он не закроется, без статуса ошибка
// в трейсе будет выглядеть успехом.
func Span(ctx context.Context, name string, fn func(context.Context) error) error {
	ctx, span := otel.Tracer("app").Start(ctx, name)
	defer span.End()

	if err := fn(ctx); err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return err
	}
	return nil
}
```

## HTTP: продолжить чужой трейс и не оборвать свой

```go
package tracinghttp

import (
	"net/http"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/propagation"
)

// Middleware — достаёт traceparent из заголовков и делает его родителем контекста
// запроса. Без этого каждый входящий запрос — новый трейс.
func Middleware(next http.Handler) http.Handler {
	tracer := otel.Tracer("http")
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ctx := otel.GetTextMapPropagator().Extract(r.Context(), propagation.HeaderCarrier(r.Header))

		ctx, span := tracer.Start(ctx, r.Method+" "+r.URL.Path)
		defer span.End()
		// r.URL.Path — кардинальность по каждому id в URL. Когда роут известен,
		// пишите шаблон: span.SetAttributes(attribute.String("http.route", "/users/{id}")).
		span.SetAttributes(
			attribute.String("http.request.method", r.Method),
			attribute.String("url.path", r.URL.Path),
		)

		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// Do — исходящий запрос с текущим контекстом: трейс продолжается в другом сервисе.
// ctx внутри req должен быть тем же контекстом, что и у span'а выше по стеку.
func Do(req *http.Request) (*http.Response, error) {
	otel.GetTextMapPropagator().Inject(req.Context(), propagation.HeaderCarrier(req.Header))
	return http.DefaultClient.Do(req) // транспорт — общий клиент с таймаутами (http-client.md)
}
```

## Pitfalls

- **Нет shutdown**: батчер отправляет спаны пачками; процесс умер без `Shutdown` —
  последние трейсы пропали, и «самое интересное» (последний запрос перед падением)
  не виден.
- **ctx потерялся по дороге**: span'ы создаются от `context.Background()` —
  получается лес несвязанных трейсов. `ctx` обязан течь через все слои
  ([context.md](context.md)).
- **Высокая кардинальность имён**: span с сырым URL (`/users/42/orders`) — это
  тысячи «операций» в бэкенде и нечитаемые агрегаты. Имя = операция или шаблон роута.
- **Секреты в атрибутах**: тело запроса, Authorization, токены в `span.SetAttributes`
  попадают в трейс-бэкенд, где доступ шире, чем к секрет-стору.
- **Сэмплирование «всё» на проде**: 100% трейсов на высоконагруженном сервисе —
  это деньги и место; ParentBased + доля, а 100% — для критичного маршрута.
- **Логи без trace_id**: трейс ищется по `trace_id`; если в логах его нет
  (`slog.String("trace_id", trace.SpanContextFromContext(ctx).TraceID().String())`),
  связка «лог ↔ трейс» не работает ([logging.md](logging.md)).
- **Два источника контекста**: свой `requestID` в заголовке и `traceparent` живут
  раздельно и расходятся при первом же неаккуратном клоне запроса.

## Related

- [../shared/observability.md](../../shared/observability.md) — три столпа и что зачем
- [logging.md](logging.md) — trace_id в логах
- [http-server.md](http-server.md) — куда вешать middleware
- [http-client.md](http-client.md) — транспорт, через который уходит контекст
- [graceful-shutdown.md](graceful-shutdown.md) — куда ставить shutdown трейсера
