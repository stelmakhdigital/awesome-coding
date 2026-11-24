---
id: react-heavy-widget
title: "React: тяжёлый виджет — ленивая загрузка, императивный API, dispose, Activity"
lang: react
min_version: "19.3"
category: snippet
tags: [lazy, suspense, code-splitting, monaco, excalidraw, lifecycle, dispose, activity, performance]
status: stable
updated: 2026-11-25
---

# Тяжёлый виджет: ленивая загрузка, императивный API, dispose, Activity

**Когда использовать** — в приложении есть объект вне React, весящий мегабайты: редактор кода (Monaco), холст (Excalidraw, tldraw), карта, чарт-движок.
**Когда НЕ использовать** — лёгкая библиотека на 20 КБ: `lazy` добавит запрос и `fallback`, выигрыша не даст. Сначала размер чанка в `dist/assets`, потом решение.

## Отдельный чанк

```tsx
// src/Whiteboard.tsx       — сам виджет, его никто не импортирует статически
// src/EditorTab.tsx        — здесь граница ленивой загрузки
import { lazy, Suspense, type ReactElement } from "react";

const Whiteboard = lazy(() => import("./Whiteboard")); // отдельный чанк (vite.md)

export function BoardTab(): ReactElement {
  return (
    // Fallback держит высоту: без неё страница подпрыгивает, а скролл уезжает.
    // Ошибка загрузки чанка (нет сети, деплой сменил хэш файла) — ErrorBoundary
    // выше по дереву; без него — белый экран без объяснения причины.
    <Suspense fallback={<div style={{ minHeight: 480 }} aria-busy="true" />}>
      <Whiteboard />
    </Suspense>
  );
}
```

Динамический импорт без `Suspense` роняет рендер; `Suspense` без ленивого импорта ничего не экономит. Нужны оба.

## Жизненный цикл стороннего объекта

```tsx
import { useEffect, useRef, useState, type ReactElement } from "react";

/** Минимальный интерфейс стороннего объекта: всё, что нужно React-обёртке. */
export type WidgetHandle = {
  setValue(value: string): void;
  getValue(): string;
  dispose(): void;
};

export type WidgetFactory = (host: HTMLElement, onChange: (value: string) => void) => WidgetHandle;

type Props = {
  factory: WidgetFactory;
  value: string;
  onChange: (value: string) => void;
};

export function WidgetPane({ factory, value, onChange }: Props): ReactElement {
  const [host, setHost] = useState<HTMLElement | null>(null);
  const [ready, setReady] = useState(false);
  const handle = useRef<WidgetHandle | null>(null);

  // Узел — через state, а не ref+effect с «а уже смонтировалось?»: эффект
  // переподписывается на появление настоящего узла.
  useEffect(() => {
    if (!host) return;
    const w = factory(host, onChange);
    handle.current = w;
    setReady(true);
    return () => {
      w.dispose(); // без этого библиотека переживает компонент: воркер, слушатели, память
      handle.current = null;
      setReady(false);
    };
  }, [host, factory, onChange]);

  // Внешнее значение → внутрь виджета императивно, и только когда оно правда
  // отличается: setValue на каждый рендер сбрасывает курсор и историю undo.
  useEffect(() => {
    const w = handle.current;
    if (w && w.getValue() !== value) w.setValue(value);
  }, [value, ready]);

  return <div ref={setHost} style={{ minHeight: 320 }} aria-busy={!ready} />;
}
```

Правила, которые зашиты в этот код:

1. Создание — в эффекте на конкретном узле, удаление — в том же cleanup. `dispose()` безусловный: «может, ещё пригодится» означает утечку воркера редактора на каждую смену вкладки.
2. Изменение внутри виджета уходит наружу через `onChange` с дебаунсом 200-400 мс на запись в стор или на сервер — не на каждый keystroke.
3. `factory` и `onChange` должны быть стабильны (`useCallback` у родителя или проп-константа), иначе эффект пересоздаёт виджет на каждый рендер. Это то место, где `useCallback` нужен, а не «на всякий случай».
4. Тяжёлый виджет не должен монтироваться в контейнере нулевой ширины — см. [effects.md](effects.md) (ResizeObserver + порог ширины).

## Скрытая вкладка: Activity

```tsx
import { Activity, useState, type ReactElement } from "react";

type Tab = "editor" | "board" | "log";

const TITLES: Record<Tab, string> = { editor: "Редактор", board: "Доска", log: "Лог" };

export function Workspace({
  panes,
}: {
  panes: Record<Tab, ReactElement>;
}): ReactElement {
  const [tab, setTab] = useState<Tab>("editor");

  return (
    <div>
      <nav aria-label="Раздел">
        {(Object.keys(TITLES) as Tab[]).map((id) => (
          <button key={id} type="button" aria-current={tab === id ? "true" : undefined} onClick={() => setTab(id)}>
            {TITLES[id]}
          </button>
        ))}
      </nav>
      {/* Условный рендер прятал бы доску размонтированием: потеря наброска,
          пересоздание холста, обнуление history undo. Activity скрывает subtree,
          сохраняя состояние и подписки (19.2). */}
      {(Object.keys(TITLES) as Tab[]).map((id) => (
        <Activity key={id} mode={tab === id ? "visible" : "hidden"}>
          {panes[id]}
        </Activity>
      ))}
    </div>
  );
}
```

`<Activity>` не откладывает загрузку (это `lazy`) и не заменяет `Suspense`: он про «скрыто, но живо». Скрытый экран, который подписан на WebSocket и жжёт CPU перерисовками, — кандидат на размонтирование; экран, где пользователь оставил черновик, — кандидат на `Activity`.

## Что мерить перед решением

| Метрика | Где взять | О чём говорит |
|---|---|---|
| Размер чанка до/после `lazy` | `dist/assets/*.js`, `gzip -c f \| wc -c` | меньше 50 КБ gzip — игра не стоит свеч |
| Интерактивность первого экрана | профиль в `vite preview`, Lighthouse | виджет не на первом экране → `lazy` обязателен |
| Память после «открыл-закрыл» ×5 | heap snapshot до/после | рост на каждый цикл — `dispose` не вызывается |

## Related

- [effects.md](effects.md) — cleanup, AbortController, подписка на размер контейнера
- [components.md](components.md) — ref-callback с очисткой (короткая форма для синхронных случаев)
- [vite.md](vite.md) — `codeSplitting.groups`, чтобы виджет не уехал в общий чанк
- [../shared/observability.md](../../shared/observability.md) — метрики, по которым видно «тормозит» не React
- [../architecture/patterns/layered.md](../../architecture/patterns/layered.md) — обёртка над библиотекой как отдельный слой
