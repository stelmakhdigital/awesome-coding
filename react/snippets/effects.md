---
id: react-effects
title: "React: границы useEffect — отмена, cleanup, effect event"
lang: react
min_version: "19.3"
category: snippet
tags: [hooks, useeffect, cleanup, abortcontroller, strictmode, effect-event, resize-observer]
status: stable
updated: 2026-11-25
---

# Границы useEffect: отмена, cleanup, effect event

**Когда использовать** — нужно выйти за пределы React: подписка на DOM/браузерные API, сторонний императивный объект, запрос, у которого нет события-обработчика.
**Когда НЕ использовать** — вычисления из пропсов, загрузка по клику/сабмиту, «синхронизация» одного стейта с другим, подписка на стор своего приложения. Каждый из этих случаев решается без эффекта (таблица ниже).

## Чем заменить эффект

| Зачем был эффект | Решается |
|---|---|
| `filtered` пересчитать при смене `query` | вычисление в рендере ([state.md](state.md)) |
| Перезагрузить данные при смене `id` | `key={id}` на компоненте экрана |
| Отправить запрос по кнопке | обработчик `onClick`/`onSubmit` |
| Реагировать на изменение пропса «как на событие» | то же событие, которое этот проп поменяло |
| Подписаться на стор вне React | `useSyncExternalStore` |
| Инкапсулировать запрос + отмену + состояние | хук-обёртка, вызываемая из обработчика, или библиотека кэша данных |

## Подписка с отменой и effect event

```tsx
import { useEffect, useEffectEvent, useRef, useState, type ReactElement } from "react";

type Stats = { cpu: number };

type Props = {
  jobId: string;
  /** Меняется на каждый рендер — и не должна переподписывать поток. */
  onSample?: (s: Stats) => void;
};

export function JobStream({ jobId, onSample }: Props): ReactElement {
  const [stats, setStats] = useState<Stats | null>(null);
  // Нестабильное значение, нужное внутри эффекта, — effect event (19.2):
  // читает свежие пропсы, но сам идентификатор стабилен и не уходит в deps.
  const report = useEffectEvent((s: Stats) => {
    onSample?.(s);
  });

  useEffect(() => {
    const ac = new AbortController();
    let alive = true;

    const pump = async (): Promise<void> => {
      try {
        const res = await fetch(`/api/jobs/${jobId}/stream`, { signal: ac.signal });
        if (!res.body) return;
        const reader = res.body.getReader();
        const dec = new TextDecoder();
        while (alive) {
          const { done, value } = await reader.read();
          if (done) break;
          const s: Stats = { cpu: dec.decode(value).length };
          if (!alive) break;
          setStats(s);
          report(s);
        }
      } catch (err) {
        if (!ac.signal.aborted) console.error("поток оборвался", err);
      }
    };
    void pump();

    // AbortController заодно даёт отмену серверу: ушедший клиент перестаёт
    // потреблять поток, а не «просто игнорирует результат».
    return () => {
      alive = false;
      ac.abort();
    };
  }, [jobId, report]);

  return <output>{stats ? `cpu ${stats.cpu}` : "нет данных"}</output>;
}
```

`StrictMode` в dev монтирует subtree дважды. Флаг «уже запускали» вместо cleanup превращает эту проверку в молчание: настоящий баг — отсутствие отмены — останется в проде, где второй монтирования нет, а утечка потока на смене `jobId` — есть.

## Размер контейнера и ref-cleanup

```tsx
import { useEffect, useRef, useState, type ReactElement } from "react";

export function CanvasBox({
  children,
  minWidth = 320,
}: {
  children: (width: number) => ReactElement;
  minWidth?: number;
}): ReactElement {
  const host = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) setWidth(Math.round(e.contentRect.width));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div ref={host}>
      {width >= minWidth ? children(width) : <p role="status">Ждём размер…</p>}
    </div>
  );
}
```

Тяжёлый виджет (редактор, холст) не должен монтироваться, пока у контейнера нет ширины: инициализация в нулевом контейнере даёт нулевой canvas и перекос координат, который потом «чинят» таймаутом.

## Related

- [heavy-widget.md](heavy-widget.md) — жизненный цикл стороннего объекта и `dispose`
- [state.md](state.md) — внешний стор вместо подписки в эффекте
- [../shared/debugging.md](../../shared/debugging.md) — как искать «запрос уходит дважды»
- [../go/snippets/http-server.md](../../go/snippets/http-server.md) — серверная сторона потоющего ответа, который здесь читается
