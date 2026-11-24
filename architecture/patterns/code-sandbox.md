---
id: arch-code-sandbox
title: "Песочница для чужого кода: лимиты, таймаут, что контейнер не защищает"
lang: architecture
min_version: null
category: pattern
tags: [sandbox, untrusted-code, isolation, docker, limits, timeout, cidfile, security, gvisor, oom]
status: stable
updated: 2026-11-25
---

# Песочница для чужого кода

Одноразовое окружение, в котором код, написанный не вами, получает задачу,ограниченный бюджет ресурсов и не получает ничего лишнего.

**Когда использовать** — приложение исполняет то, что принёс пользователь: проверяющая система для тестового задания, «запусти мой сниппет», плагин-хост, генератор отчётов на скриптах клиента, автомат с ревью, который собирает чужую ветку.
**Когда НЕ использовать** — код пришёл из вашего же репозитория и прошёл ревью (тогда обычная сборка в CI); выполняется ваш собственный код с параметрами пользователя (нужен разбор аргументов, а не изоляция); нужен «песочница для разработки» — это контейнер без лимитов и это не песочница.

## Контракт прогона

Прежде чем выбирать технологию, зафиксируйте, что обещаете. Типовой контракт для «пользователь прислал код»:

| Пункт | Значение | Почему это контракт, а не настройка |
|---|---|---|
| Бюджет времени | например 30 с на сборку + 60 с на выполнение | без границы любой цикл висит; клиенту нужен ответ |
| Память | 512 МиБ | без лимита один прогон съедает узел |
| Процессы | 128 | вилка-бомба `:(){ :\|:& };:` без лимита pid — отказ узла |
| Сеть | отсутствует | иначе слив секретов из окружения и побеги за зависимостями |
| Файловая система | только каталог прогона на запись, всё остальное read-only | запись вне каталога — это уже атака на хост |
| Вывод | потолок, например 1 МиБ, с пометкой об обрезке | `while true; do echo; done` не должен стать вашим логом |
| Код таймаута | отдельный (например 124) и отличаться от «упало» | «не успел» и «неправильно» — разные ответы пользователю |
| Отсутствие изолятора | честная 503 и явная ошибка | тихий откат в «выполнить локально» = дыра |

## Запуск в контейнере

```bash
#!/usr/bin/env bash
# shellcheck shell=bash
# sandbox-run.sh — минимально привилегированный прогон чужого кода.
set -euo pipefail

WORK_DIR="$1"; shift          # каталог прогона: входные файлы, права 0700
IMAGE="$1"; shift             # образ языка, без тегов «latest»
CID_FILE="${CID_FILE:-$(mktemp -u -t sandbox-cid-XXXXXX)}"
TIMEOUT_SECS="${TIMEOUT_SECS:-60}"

# CID-файл не должен существовать: docker CLI 27+ отказывается запускать
# (`container ID file found`, exit 125), если путь занят. mktemp -u даёт имя
# без создания файла.
exec timeout -k 10s "$TIMEOUT_SECS" docker run --rm \
  --network=none \
  --cpus=1 \
  --memory=512m \
  --pids-limit=128 \
  --read-only \
  --tmpfs /tmp:size=128m,exec \
  --cap-drop=ALL \
  --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" \
  --cidfile "$CID_FILE" \
  --volume "$WORK_DIR:/work:rw" \
  "$IMAGE" sh -c 'cd /work && "$@"' sh "$@"
```

Почему именно так, по флагом:

- `--read-only` + `--tmpfs /tmp:…,exec`. По умолчанию `--tmpfs` монтируется с `noexec`, и собранный бинарник, положенный на `/tmp`, не запустится: `fork/exec … permission denied`. Для одноразового контейнера за лимитами pid/памяти/сети `exec` на `/tmp` — осознанный выбор.
- `--user "$(id -u):$(id -g)"`. Без `--user` контейнер пишется в примонтированный каталог от root, и на хосте остаются файлы-собственники `root`, которые следующий прогон не сможет ни удалить, ни перечитать. Привязка к своему uid удобна, но помните: это **ваш** пользователь на хосте, и всё, что ему доступно вне `/work`, доступно и процессу из контейнера.
- `--cidfile` нужен не для логов, а для убийства: по таймауту надо остановить контейнер, а не только клиента `docker`.
- Проверяющая программа (градатор, линтер, эталон) монтируется отдельно и только на чтение — иначе решение кандидата подменит того, кто его оценивает. Права не спасут, если оценка лежит в том же каталоге на запись.
- Переменные окружения передаются списком по имени. `--env-file` со всем окружением сервиса — это выдача токенов внутрь чужого процесса.

## Убийство по таймауту

```go
// Package sandbox — прогон чужого кода в контейнере с честным таймаутом.
package sandbox

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
)

// ErrNoRunner — docker не поднялся. Прогон обязан остановиться на этом,
// а не «выполнить локально».
var ErrNoRunner = errors.New("изолятор недоступен")

// Код возврата прогона: 124 — не уложился в бюджет.
const CodeTimeout = 124

type Limits struct {
	Timeout time.Duration
	Memory  string
	CPUs    string
	PIDs    string
}

func DefaultLimits() Limits {
	return Limits{Timeout: 60 * time.Second, Memory: "512m", CPUs: "1", PIDs: "128"}
}

type cappedWriter struct {
	mu        sync.Mutex
	buf       bytes.Buffer
	limit     int
	truncated bool
}

func (w *cappedWriter) Write(p []byte) (int, error) {
	w.mu.Lock()
	defer w.mu.Unlock()

	// Возвращаем len(p) всегда: иначе exec считает запись неудавшейся и убьёт
	// процесс за «ошибку записи», а нам нужен его код возврата.
	if w.buf.Len()+len(p) > w.limit {
		if !w.truncated {
			w.buf.WriteString("\n… вывод обрезан по лимиту\n")
			w.truncated = true
		}
		return len(p), nil
	}
	w.buf.Write(p)
	return len(p), nil
}

func (w *cappedWriter) Bytes() []byte {
	w.mu.Lock()
	defer w.mu.Unlock()
	return append([]byte(nil), w.buf.Bytes()...)
}

// Run выполняет cmd в образе image в каталоге workDir.
func Run(ctx context.Context, image, workDir, cmd string, lim Limits) (out []byte, code int, err error) {
	cidPath, err := newCIDPath()
	if err != nil {
		return nil, -1, err
	}
	defer os.Remove(cidPath)

	args := []string{
		"run", "--rm", "--network=none",
		"--cpus", lim.CPUs, "--memory", lim.Memory, "--pids-limit", lim.PIDs,
		"--read-only", "--tmpfs", "/tmp:size=128m,exec",
		"--cap-drop", "ALL", "--security-opt", "no-new-privileges",
		"--user", fmt.Sprintf("%d:%d", os.Getuid(), os.Getgid()),
		"--cidfile", cidPath,
		"-v", workDir + ":/work:rw",
		image, "sh", "-c", "cd /work && " + cmd,
	}

	// Не exec.CommandContext: по дедлайну он убивает только клиента `docker run`,
	// а контейнер остаётся на daemon и копит ресурсы (--rm не сработает, пока
	// контейнер жив). Убиваем контейнер сами — по cid из файла.
	cmdRun := exec.Command("docker", args...)
	tw := &cappedWriter{limit: 1 << 20}
	cmdRun.Stdout, cmdRun.Stderr = tw, tw

	if err := cmdRun.Start(); err != nil {
		if errors.Is(err, exec.ErrNotFound) {
			return nil, -1, ErrNoRunner
		}
		return nil, -1, fmt.Errorf("sandbox start: %w", err)
	}

	done := make(chan error, 1)
	go func() { done <- cmdRun.Wait() }()

	rctx, cancel := context.WithTimeout(ctx, lim.Timeout)
	defer cancel()

	select {
	case waitErr := <-done:
		// Успел сам. Если при этом истёк внешний контекст — это отмена клиента,
		// её тоже надо отдать различимо.
		if ctxErr := ctx.Err(); ctxErr != nil {
			return tw.Bytes(), exitCode(waitErr), ctxErr
		}
		return tw.Bytes(), exitCode(waitErr), nil

	case <-rctx.Done():
		killByCID(cidPath)
		<-done
		if errors.Is(ctx.Err(), context.Canceled) {
			return tw.Bytes(), CodeTimeout, context.Canceled
		}
		return tw.Bytes(), CodeTimeout, nil
	}
}

// newCIDPath — путь без файла: docker CLI 27+ отказывается запускать контейнер,
// если cidfile уже существует (exit 125). Старые версии CLI это проглатывали,
// поэтому прогон, работавший вчера, после обновления docker падает на каждом
// запуске.
func newCIDPath() (string, error) {
	f, err := os.CreateTemp("", "sandbox-cid-*")
	if err != nil {
		return "", err
	}
	path := f.Name()
	_ = f.Close()
	if err := os.Remove(path); err != nil {
		return "", fmt.Errorf("cidfile: %w", err)
	}
	return path, nil
}

func killByCID(cidPath string) {
	data, err := os.ReadFile(cidPath)
	if err != nil {
		return
	}
	cid := strings.TrimSpace(string(data))
	if cid == "" {
		return
	}
	// Отдельный контекст: рабочий уже истёк, а убить надо.
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = exec.CommandContext(ctx, "docker", "kill", cid).Run()
}

func exitCode(err error) int {
	var ee *exec.ExitError
	if errors.As(err, &ee) {
		return ee.ExitCode() // 137 — OOM-kill, 124 — таймаут внешнего timeout
	}
	return 0
}
```

## Что контейнер с runc не закрывает

| Реальность | Последствие | Что с этим делать |
|---|---|---|
| Docker daemon доступен через смонтированный `docker.sock` | процесс внутри может создать привилегированный контейнер и смонтировать корень хоста: это root на хосте, а не «изоляция» | сокет внутрь прогона не монтировать вообще; если нужен второй контейнер из первого — отдельный сервис-исполнитель за API, с собственными правами |
| Ядро одно на всех | побег через уязвимость ядра — вопрос времени и желания | при настоящем внешнем противнике: gVisor (`runsc`), Kata или microVM (Firecracker); цена — запуск медленнее, часть системных вызовов недоступна |
| `--user` = uid хоста | доступ ко всему, что принадлежит этому пользователю вне `/work` | отдельный системный пользователь без домашней директории и без ключей; примонтировано ровно то, что нужно, и только нужными правами |
| Переменные окружения прогона | секреты сервиса уходят внутрь чужого процесса | белый список переменных; секреты — не в env прогона, а в токене на один прогон |
| Файлы, оставшиеся от прогона | мусор и право на перезапись чужого каталога | каталог прогона создаётся под конкретный uid, удаление — под тем же uid, с `--user` это перестает быть «root-магией» |
| Кэш инструментов (Go build cache, pip, npm) | tmpfs 128 МиБ кончается на линковке, а без кэша каждый прогон качает зависимости по сети (которой нет) | отдельный том на кэш, смонтированный на запись; размер — по факту, не на глаз |

## Разные языки — разные лимиты

| Язык | Что учитывать |
|---|---|
| Go | тулчейн резервирует большой адресный простор и активно пишет кэш сборки: лимиты по RSS и по виртуальной памяти ведут себя по-разному, а `GOCACHE` в тесном tmpfs ломает линковку |
| Python | `RLIMIT_AS` и cgroup по памяти не одно и то же; OOM выглядит как `Killed` (137), а не как `MemoryError` |
| Node | лимит кучи (`--max-old-space-size`) и лимит контейнера должны согласоваться, иначе V8 умирает раньше cgroup |
| C/C++ | `RLIMIT_*` полезны сверх cgroup: сборка мусора не спасёт, а `-fsanitize=address` в проверяющей сборке полезен |
| Любая сборка | таймер на «сборка» и на «выполнение» нужен раздельно: 60 с на сборку крупного проекта — это не таймаут решения, а неверный бюджет |

## Тесты изоляции

Изоляция без тестов — это флаги, которые никто не проверял после обновления. Минимальный набор, каждый из которых обязан проваливаться, если лимит слетел:

1. **Сеть недоступна.** Внутри — `dial` на внешний адрес с коротким таймаутом; ожидание: ошибка. Работает и как тест на `--network=none`, и как тест на то, что образ не протаскивает резолвер.
2. **Память ограничена.** Аллокация за лимитом → 137, а не «висит».
3. **Процессы ограничены.** Fork-бомба с ограничением по количеству детей → отказ в создании процесса, узел жив.
4. **Таймаут убивает контейнер, а не только клиента.** После прогона — список контейнеров по cid: пусто. Этот тест ловит ровно ту ошибку, которую `exec.CommandContext` прячет: клиент мёртв, контейнер жив.
5. **Вывод обрезан.** Прогон, печатающий больше потолка, возвращает помеченный усечённый вывод и валидный код возврата.
6. **Изолятор недоступен → 503, и никакого локального выполнения.** Проверяется запуском без docker.

## Related

- [../../go/snippets/proxy.md](../../go/snippets/proxy.md) — прокси к сервису-исполнителю: 503 против 504 и границы времени
- [../../go/snippets/context.md](../../go/snippets/context.md) — отмена, которая доходит до исполнителя
- [../../go/snippets/metrics.md](../../go/snippets/metrics.md) — длительность прогонов, доля таймаутов, отказы изолятора
- [../../cicd/docker.md](../../cicd/docker.md) — образы и HEALTHCHECK
- [../../agenting/rules.md](../../agenting/rules.md) — что разрешено автоматизации, которая такой песочницей пользуется
- [patterns/layered.md](layered.md) — сервис-исполнитель как отдельный слой
