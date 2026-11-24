---
id: go-metrics
title: "Go: метрики Prometheus — RED-middleware, healthz, бизнес-метрики"
lang: go
min_version: "1.22"
category: snippet
tags: [metrics, prometheus, observability, healthz, readiness, histogram, cardinality, pprof, red]
status: stable
updated: 2026-11-25
---

# Метрики Prometheus: RED-middleware, healthz, бизнес-метрики

**Когда использовать** — сервису нужны цифры до первого инцидента: частота и длительность запросов, очередь, активные соединения, а также раздельные точки «жив» и «готов». Библиотека — `github.com/prometheus/client_golang` v1.25.
**Когда НЕ использовать** — трейсы и логи вместо метрик не пишутся ([tracing.md](tracing.md), [logging.md](logging.md)); per-user и per-request-id лейблы; метрики как единственный канал для «что именно упало».

## Реестр и HTTP-middleware

```go
// Package metrics — метрики HTTP: частота, длительность, в работе.
package metrics

import (
	"net/http"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/collectors"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// Buckets под типовой API: 5 мс — внутренний кэш, 2 с — отчёт. Дефолтные
// Buckets Prometheus заканчиваются на 10 с, и p95 «провисает» между ними.
var Buckets = []float64{.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10}

type HTTP struct {
	requests *prometheus.CounterVec
	duration *prometheus.HistogramVec
	inFlight prometheus.Gauge
}

func New(reg *prometheus.Registry) *HTTP {
	h := &HTTP{
		requests: prometheus.NewCounterVec(prometheus.CounterOpts{
			Namespace: "app", Subsystem: "http", Name: "requests_total",
			Help: "Количество ответов по маршруту, методу и статусу.",
		}, []string{"route", "method", "status"}),
		duration: prometheus.NewHistogramVec(prometheus.HistogramOpts{
			Namespace: "app", Subsystem: "http", Name: "request_duration_seconds",
			Help:    "Длительность обработки запроса.",
			Buckets: Buckets,
		}, []string{"route", "method"}),
		inFlight: prometheus.NewGauge(prometheus.GaugeOpts{
			Namespace: "app", Subsystem: "http", Name: "in_flight",
			Help: "Запросы, обрабатываемые прямо сейчас.",
		}),
	}

	reg.MustRegister(
		h.requests, h.duration, h.inFlight,
		collectors.NewGoCollector(),
		collectors.NewProcessCollector(collectors.ProcessCollectorOpts{}),
	)
	return h
}

// Middleware считает по паттерну маршрута, а не по пути запроса. Лейбл «route»
// со значением /users/42 превращает метрики в счётчик уникальных URL: память
// Prometheus растёт, а скрейп замедляется. Это главный способ уронить мониторинг
// приложением.
func (h *HTTP) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		h.inFlight.Inc()
		defer h.inFlight.Dec()

		start := time.Now()
		rec := &statusWriter{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)

		route := r.Pattern
		if route == "" {
			route = "unmatched"
		}
		h.requests.WithLabelValues(route, r.Method, strconv.Itoa(rec.status)).Inc()
		h.duration.WithLabelValues(route, r.Method).Observe(time.Since(start).Seconds())
	})
}

// Handler — отдаёт реестр. Отдельный listener для него — ниже, в health.
func Handler(reg *prometheus.Registry) http.Handler {
	return promhttp.HandlerFor(reg, promhttp.HandlerOpts{
		// Ошибка одной метрики не должна обрывать весь скрейп.
		ErrorHandling: promhttp.ContinueOnError,
	})
}

// statusWriter записывает статус. Flush и Unwrap обязательны: без них обёртка
// ломает стриминг (SSE и вообще всё, что пишется частями), Range и http.ResponseController —
// ошибки вида «ResponseWriter does not implement http.Flusher» приходят в проде,
// а не в тестах.
type statusWriter struct {
	http.ResponseWriter
	status int
}

func (w *statusWriter) WriteHeader(code int) {
	w.status = code
	w.ResponseWriter.WriteHeader(code)
}

func (w *statusWriter) Flush() {
	if f, ok := w.ResponseWriter.(http.Flusher); ok {
		f.Flush()
	}
}

func (w *statusWriter) Unwrap() http.ResponseWriter { return w.ResponseWriter }
```

## healthz, readyz и отдельный порт метрик

```go
// Package health — разделение «процесс жив», «процесс может работать» и
// «внутренние данные процесса».
package health

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/pprof"
	"time"
)

// Check — зависимость с собственным таймаутом. Общий бюджет обязан быть меньше
// таймаута балансировщика, иначе «readiness» просто успевает стать 503 позже.
type Check struct {
	Name    string
	Timeout time.Duration
	Probe   func(ctx context.Context) error
}

// Liveness — ответ на вопрос «не завис ли процесс». Проверок зависимостей здесь
// нет: БД легла на минуту, и оркестратор убьёт все поды, которые могли бы
// пережить этот провал и продолжить обслуживать кэш.
func Liveness() http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok\n"))
	})
}

// Readiness — «готов принимать трафик». Проверяются только то, без чего запрос
// гарантированно упадёт: соединение с БД, миграция, диск.
func Readiness(checks []Check) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		results := make(map[string]string, len(checks))
		bad := 0

		for _, c := range checks {
			ctx, cancel := context.WithTimeout(r.Context(), c.Timeout)
			err := c.Probe(ctx)
			cancel()
			if err != nil {
				bad++
				results[c.Name] = err.Error()
				continue
			}
			results[c.Name] = "ok"
		}

		status := http.StatusOK
		if bad > 0 {
			status = http.StatusServiceUnavailable
		}
		w.Header().Set("content-type", "application/json")
		w.WriteHeader(status)
		_ = json.NewEncoder(w).Encode(map[string]any{"checks": results})
	})
}

// Admin — метрики и pprof на отдельном адресе. Наружу (0.0.0.0 на публичном
// интерфейсе) их выносить нечего: /debug/pprof/heap отдаёт структуру процесса,
// а /metrics — имена коллекций и версии.
func Admin(addr string, metrics http.Handler) *http.Server {
	mux := http.NewServeMux()
	mux.Handle("/metrics", metrics)
	mux.HandleFunc("/debug/pprof/", pprof.Index)
	mux.HandleFunc("/debug/pprof/heap", pprof.Handler("heap").ServeHTTP)
	mux.HandleFunc("/debug/pprof/goroutine", pprof.Handler("goroutine").ServeHTTP)
	mux.HandleFunc("/debug/pprof/profile", pprof.Profile)

	return &http.Server{
		Addr:              addr, // «127.0.0.1:9090» — и только
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}
}
```

## Бизнес-метрики в воркере

```go
// Package jobs — метрики длинной работы: длительность, исход, очередь.
package jobs

import (
	"context"
	"errors"
	"time"

	"github.com/prometheus/client_golang/prometheus"
)

type Metrics struct {
	run     prometheus.Histogram
	outcome *prometheus.CounterVec
	queued  *prometheus.GaugeVec
}

func NewMetrics(reg *prometheus.Registry) *Metrics {
	m := &Metrics{
		run: prometheus.NewHistogram(prometheus.HistogramOpts{
			Namespace: "app", Subsystem: "job", Name: "run_duration_seconds",
			Help:    "Длительность выполнения задачи.",
			Buckets: []float64{.1, .5, 1, 5, 15, 60, 300, 900},
		}),
		// Исход — конечное множество. Лейблы «taskID» или «userID» здесь быть не
		// может: кардинальность = число задач.
		outcome: prometheus.NewCounterVec(prometheus.CounterOpts{
			Namespace: "app", Subsystem: "job", Name: "runs_total",
			Help: "Завершённые задачи по исходу.",
		}, []string{"kind", "outcome"}),
		queued: prometheus.NewGaugeVec(prometheus.GaugeOpts{
			Namespace: "app", Subsystem: "job", Name: "queued",
			Help: "Задач в очереди (наблюдается перед выборкой).",
		}, []string{"kind"}),
	}
	reg.MustRegister(m.run, m.outcome, m.queued)
	return m
}

// Observe — один вызов на завершённую задачу.
func (m *Metrics) Observe(kind string, started time.Time, err error) {
	m.run.Observe(time.Since(started).Seconds())

	outcome := "ok"
	switch {
	case err == nil:
	case errors.Is(err, context.DeadlineExceeded):
		outcome = "timeout"
	default:
		outcome = "error"
	}
	m.outcome.WithLabelValues(kind, outcome).Inc()
}

func (m *Metrics) SetQueued(kind string, n float64) { m.queued.WithLabelValues(kind).Set(n) }
```

## Что с этим читать

| Вопрос | Запрос |
|---|---|
| Доля ошибок по маршруту | `sum(rate(app_http_requests_total{status=~"5.."}[5m])) / sum(rate(app_http_requests_total[5m]))` |
| p95 длительности | `histogram_quantile(0.95, sum by (le, route) (rate(app_http_request_duration_seconds_bucket[5m])))` |
| Очередь растёт | `avg_over_time(app_job_queued[10m]) > 20` |
| Утечка горутин | `go_goroutines` в тренде, затем `pprof/goroutine` |

Summary-метрики (`prometheus.NewSummary`) квантили считают на стороне процесса и не агрегируются между подами: p95 двух подов — не среднее их p95. Нужна агрегируемая квантиль — гистограмма и `histogram_quantile` ([../shared/observability.md](../../shared/observability.md)).

## Related

- [logging.md](logging.md) — логи по trace id, метрики по тренду
- [tracing.md](tracing.md) — третий сигнал: где именно внутри запроса долго
- [http-server.md](http-server.md) — таймауты сервера, обёртки ResponseWriter
- [websocket.md](websocket.md) — gauge активных соединений
- [../shared/observability.md](../../shared/observability.md) — RED/golden signals, что алертить
- [../cicd/docker.md](../../cicd/docker.md) — HEALTHCHECK и `start_period` под readiness
