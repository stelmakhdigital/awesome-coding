---
id: go-periodic-jobs
title: "Go: периодическая работа — тикер, пропуск тика, backoff, один экземпляр"
lang: go
min_version: "1.22"
category: snippet
tags: [ticker, schedule, background-job, cron, backoff, jitter, overlap, single-instance, flock]
status: stable
updated: 2026-11-24
---

# Периодическая работа: тикер, пропуск тика, backoff, один экземпляр

**Когда использовать** — задача повторяется внутри живого процесса: обновить кэш, стянуть курсы, подчистить temp, сбросить метрики, пересчитать рейтинг. Интервал от секунд до часов, состояние (кэш, соединения) переиспользуется.
**Когда НЕ использовать** — запуск не зависит от процесса и должен пережить его рестарт, нужна история запусков и алерт на пропуск: это внешний планировщик (таблица ниже). Задач много, они разные и описываются пользователями — нужен реестр с состоянием, а не цикл в `main`. Один запуск по времени («в 03:00 1 января») — планировщик, не тикер: тикер считает от старта процесса, а не от стенных часов.

## Цикл: тикер, отмена, пропуск наложения

```go
// Package jobs — повторяющаяся задача внутри процесса: тикер, отмена через ctx,
// пропуск тика, если предыдущий ещё идёт, и защита от паники в задаче.
package jobs

import (
	"context"
	"log/slog"
	"runtime/debug"
	"time"
)

// Job — повторяющаяся задача.
type Job struct {
	Name  string
	Every time.Duration
	// Task — сама работа. Ошибка не завершает цикл: она уходит в журнал и в
	// backoff, если он задан.
	Task func(ctx context.Context) error
	// StartDelay — пауза перед первым запуском: дать процессу прогреться и
	// дождаться готовности зависимостей.
	StartDelay time.Duration
	// Backoff — паузы после неудач. nil — продолжать строго по расписанию.
	Backoff *Backoff
	// Log — журнал задачи; nil — slog.Default().
	Log *slog.Logger
}

// Run крутит задачу, пока ctx не отменён. Возвращает ошибку отмены; ошибку
// последнего тика отдаёт lastErr — её достаточно залогировать на выходе.
func (j *Job) Run(ctx context.Context) (lastErr error) {
	log := j.Log
	if log == nil {
		log = slog.Default()
	}
	if j.Every <= 0 {
		return nil // задача без интервала не имеет смысла; не паникуем в main
	}

	wait := time.NewTimer(j.StartDelay)
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-wait.C:
	}
	wait.Stop()

	tick := time.NewTicker(j.Every)
	defer tick.Stop() // без Stop тикер живёт до конца процесса

	// Одно место в буфере: тик, который не застал свободного, пропускается,
	// а не встаёт в очередь.
	busy := make(chan struct{}, 1)
	for {
		lastErr = j.tick(ctx, log, busy, lastErr)
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-tick.C:
		}
	}
}

// tick выполняет один запуск. Возвращает последнюю ошибку задачи.
func (j *Job) tick(ctx context.Context, log *slog.Logger, busy chan struct{}, lastErr error) error {
	select {
	case busy <- struct{}{}:
	default:
		log.Warn("пропуск: предыдущий запуск ещё идёт", "job", j.Name)
		return lastErr
	}
	defer func() { <-busy }()
	defer func() {
		if r := recover(); r != nil {
			log.Error("паника в задаче", "job", j.Name, "panic", r,
				"stack", string(debug.Stack()))
		}
	}()

	start := time.Now()
	if err := j.Task(ctx); err != nil {
		log.Error("тик не удался", "job", j.Name, "err", err, "took", time.Since(start))
		if j.Backoff != nil {
			pause := j.Backoff.Next()
			log.Info("пауза после неудачи", "job", j.Name, "pause", pause,
				"attempts", j.Backoff.Attempts())
			// Таймер, а не Sleep: отмена обязана приходить и во время паузы.
			t := time.NewTimer(pause)
			defer t.Stop()
			select {
			case <-ctx.Done():
			case <-t.C:
			}
		}
		return err
	}
	if j.Backoff != nil {
		j.Backoff.Reset()
	}
	log.Debug("тик", "job", j.Name, "took", time.Since(start))
	return lastErr
}
```

## Backoff: неудача не должна превращаться в штурм

```go
package jobs

import (
	"math"
	"math/rand/v2"
	"time"
)

// Backoff — экспоненциальная пауза после неудач с потолком и дрейфом.
// Дрейф нужен, когда экземпляров несколько: без него все одновременно
// возвращаются к провайдеру, который только что лег.
type Backoff struct {
	Base     time.Duration // пауза после первой неудачи, обычно секунда
	Cap      time.Duration // потолок: дальше расти бессмысленно, обычно минуты
	Multi    float64       // множитель, 2 достаточно
	attempts int
}

// Next вызывается после неудачи и возвращает, сколько ждать.
func (b *Backoff) Next() time.Duration {
	b.attempts++
	mult := math.Pow(b.factor(), float64(b.attempts-1))
	if math.IsInf(mult, 0) || mult > 1e6 {
		mult = 1e6
	}
	d := time.Duration(float64(b.base()) * mult)
	if limit := b.ceiling(); d > limit || d <= 0 {
		d = limit
	}
	// Дрейф в сторону уменьшения (0.5..1.0): хуже всего синхронная толпа,
	// а не слишком короткая пауза.
	return time.Duration(float64(d) * (0.5 + 0.5*rand.Float64()))
}

// Reset вызывается после успешного тика: счётчик неудач обязан обнуляться,
// иначе первая же авария навсегда оставит задачу на потолке.
func (b *Backoff) Reset() { b.attempts = 0 }

// Attempts — подряд сколько неудач накоплено (в метрику или в журнал).
func (b *Backoff) Attempts() int { return b.attempts }

func (b *Backoff) base() time.Duration {
	if b.Base <= 0 {
		return time.Second
	}
	return b.Base
}

func (b *Backoff) ceiling() time.Duration {
	if b.Cap <= 0 {
		return 5 * time.Minute
	}
	return b.Cap
}

func (b *Backoff) factor() float64 {
	if b.Multi <= 1 {
		return 2
	}
	return b.Multi
}
```

## Один экземпляр: lock на хосте

```go
package jobs

import (
	"errors"
	"fmt"
	"os"
	"syscall"
)

// Lock — единственный запущенный экземпляр на хосте. Второй процесс видит
// занятый lock и обязан уйти, а не встать в очередь: два тикера, пишущих в одну
// таблицу, дают дубли и гонку.
type Lock struct {
	f *os.File
}

// ErrBusy — экземпляр уже запущен. Ожидания здесь нет: ждущий тикер всё равно
// будет работать вдвойне.
var ErrBusy = errors.New("экземпляр уже запущен")

// AcquireLock занимает файл-lock. Держать нужно до конца работы процесса:
// lock держится открытым дескриптором и снимается самим ядром, если процесс
// умрёт — за счёт этого аварийное завершение не оставляет мёртвый lock.
func AcquireLock(path string) (*Lock, error) {
	f, err := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0o600)
	if err != nil {
		return nil, fmt.Errorf("lock %s: %w", path, err)
	}
	if err := syscall.Flock(int(f.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); err != nil {
		_ = f.Close()
		return nil, fmt.Errorf("%w: %s", ErrBusy, path)
	}
	// pid внутри: по нему видно, кто держит lock. Обрезать обязательно —
	// иначе после рестарта останется «42\n17\n» и читать будет нечего.
	if err := f.Truncate(0); err != nil {
		_ = f.Close()
		return nil, fmt.Errorf("lock %s: %w", path, err)
	}
	if _, err := fmt.Fprintf(f, "%d\n", os.Getpid()); err != nil {
		_ = f.Close()
		return nil, fmt.Errorf("lock %s: %w", path, err)
	}
	return &Lock{f: f}, nil
}

// Release отпускает lock. Вызывать при штатном завершении; при падении
// дескриптор закрывает ядро.
func (l *Lock) Release() error {
	if l == nil || l.f == nil {
		return nil
	}
	if err := syscall.Flock(int(l.f.Fd()), syscall.LOCK_UN); err != nil {
		_ = l.f.Close()
		return err
	}
	err := l.f.Close()
	l.f = nil
	return err
}

// Holder — pid процесса, держащего lock (для сообщения об ошибке).
func (l *Lock) Holder() string {
	if l == nil || l.f == nil {
		return ""
	}
	buf := make([]byte, 32)
	n, _ := l.f.ReadAt(buf, 0)
	return string(buf[:n])
}
```

Файловый lock — это **один хост**. В кластере или при нескольких репликах в одном контейнере нужен общий lock: advisory lock в PostgreSQL ([../database/snippets/transactions.md](../../database/snippets/transactions.md)) или отдельная задача-воркер, к которой обращаются все ([../agenting/snippets/lockfile.md](../../agenting/snippets/lockfile.md) — то же на bash).

## Свой цикл или внешний планировщик

| Свой цикл в процессе | Внешний планировщик (systemd timer, cron, `schedule:` в CI) |
|---|---|
| Есть прогретый кэш, соединения, клиент провайдера | Каждый запуск — холодный процесс и новый клиент |
| Нет лишней инфраструктуры, отмена через тот же `ctx` | Переживает рестарт и выкат процесса |
| Пропуск виден только из журнала процесса | История запусков, алерт на неуспех, перегон по расписанию стенных часов |
| Lock — локальный файл, в кластере не спасает | «Один экземпляр» решается одним запуском задачи |
| Короткий интервал (секунды) без боли | Интервал меньше минуты — планировщик не подходит |

Практический критерий: если после трёх пропущенных подряд запусков кто-то должен встать и посмотреть — это внешний планировщик либо метрика с алертом, а не `log.Println`.

## Ловушки

- `time.Tick` игнорирует то, что его не читают, и никогда не останавливается: в цикле с `break` тикер утекает. Нужен `NewTicker` с `defer Stop`.
- Тикер **не догоняет**: пока тик долгий, следующий тик копится один (буфер канала — 1), остальные теряются. Если догонять надо, считайте пропуски сами (`for next.Before(now) { ... }`) и решите, нужны ли они: пересчёт за 30 прошедших суток обычно не нужен.
- `time.Sleep(interval)` в конце цикла даёт drift: фактический интервал = работа + пауза. Тикер привязан к моменту запуска цикла, `Sleep` — к концу работы.
- Одна долгая задача держит выключение процесса: shutdown ждёт её до конца. Дайте тик право завершиться за N секунд (`context.WithTimeout` внутри тика), остальное — [graceful shutdown](graceful-shutdown.md).
- Ошибка в журнал без backoff = штурм провайдера раз в интервал. Успешный тик обязан сбросить счётчик, иначе первая авария навсегда оставляет задачу на потолке пауз.
- Нет защиты от наложения — задача, идущая дольше интервала, работает в два экземпляра: дубли записей, гонка за файл. Сигнал, что интервал выбран неправильно, — рост пропусков в метрике.
- Свой цикл не знает про стенные часы: `Every: 24h` от старта процесса никогда не совпадёт с «ночь с воскресенья на понедельник», а в сутки перевода часов даст 23 или 25 часов. Привязка к календарю — планировщик или пересчёт границы дня.
- Lock на файле не решает задачу в кластере: он видит только свой хост и свой контейнер.

## Related

- [graceful-shutdown.md](graceful-shutdown.md) — тот же `ctx` доживает до выключения: задача обязана успеть завершиться за отпущенные секунды
- [metrics.md](metrics.md) — пропуски и неудачи тикаются в счётчики: три пропуска подряд должны поднимать алерт, а не тонуть в журнале
- [worker-pool.md](../patterns/worker-pool.md) — когда работы больше, чем успевает один тик: ограниченный параллелизм вместо наложения
- [../agenting/snippets/lockfile.md](../../agenting/snippets/lockfile.md) — `flock` на bash, тот же единственный экземпляр
- [../database/snippets/transactions.md](../../database/snippets/transactions.md) — advisory lock, когда экземпляров несколько на разных хостах
- [state-machine.md](state-machine.md) — когда у задачи появляются стадии и ожидание внешних событий: автомат вместо тикера
