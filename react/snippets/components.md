---
id: react-components
title: "React: компонент — пропсы, слоты, ref, ключи"
lang: react
min_version: "19.3"
category: snippet
tags: [components, props, jsx, ref, children, keys, a11y, use-id]
status: stable
updated: 2026-11-24
---

# Компонент: пропсы, слоты, ref, ключи

**Когда использовать** — любой новый компонент: как описать пропсы, куда деть `ref`, как передавать вложенность и как не потерять состояние списка.
**Когда НЕ использовать** — если нужен класс с `componentDidMount`: в 19 `ReactDOM.render` и `react-dom/test-utils` удалены,только в легаси-дереве.

## Что удалено или переехало в 19

| Было | Стало |
|---|---|
| `Component.propTypes`, `defaultProps` у функции | типы TypeScript + значения по умолчанию в деструктуризации; проверка данных — схема на границе |
| `React.forwardRef((props, ref) => ...)` | `ref` — обычный проп |
| `string` refs (`ref="input"`) | `useRef` или ref-callback |
| `ReactDOM.render`, `hydrate`, `unmountComponentAtNode`, `findDOMNode` | `react-dom/client` (`createRoot`), ref-объекты |
| глобальный `JSX.Element` | `import type { JSX, ReactElement } from "react"` |
| `useRef()` без аргумента | `useRef<T | null>(null)` — аргумент обязателен |
| `element.ref` | `element.props.ref` |

## Пропсы, слот и ref

```tsx
import {
  useId,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
  type RefObject,
} from "react";

type PanelProps = {
  title: string;
  children: ReactNode;
  /** Слот, а не функция renderAction(): элемент живёт в дереве родителя. */
  action?: ReactNode;
  initialOpen?: boolean;
  /** ref — обычный проп: forwardRef в 19 не нужен. */
  bodyRef?: RefObject<HTMLDivElement | null>;
  /** Указание на ошибку: связывается с aria-invalid у содержимого. */
  describedBy?: string;
};

export function Panel({
  title,
  children,
  action,
  initialOpen = true,
  bodyRef,
  describedBy,
}: PanelProps): ReactElement {
  const [open, setOpen] = useState(initialOpen);
  const body = useRef<HTMLDivElement | null>(null);
  const headingId = useId(); // уникален и на сервере, и в клиенте: счётчик модуля — нет

  return (
    <section aria-labelledby={headingId}>
      <h2 id={headingId}>
        <button
          type="button"
          aria-expanded={open}
          aria-describedby={describedBy}
          onClick={() => setOpen((v) => !v)}
        >
          {title}
        </button>
      </h2>
      {open && (
        <div
          ref={(el) => {
            body.current = el;
            if (bodyRef) bodyRef.current = el;
            // cleanup ref-callback'а (19): старый вызов ref={null} больше не работает
            return () => {
              body.current = null;
              if (bodyRef) bodyRef.current = null;
            };
          }}
        >
          {children}
        </div>
      )}
      {action}
    </section>
  );
}
```

## Список, ключи и сброс состояний

```tsx
import { useState, type ReactElement } from "react";

export type Row = { id: string; title: string; done: boolean };

type ListProps = {
  rows: Row[];
  onSelect: (id: string) => void;
};

export function List({ rows, onSelect }: ListProps): ReactElement {
  return (
    <ul>
      {rows.map((row) => (
        // key — идентификатор сущности. Индекс массива на переставляемом списке
        // переносит состояние строки (фокус, черновик) на другого пользователя.
        <li key={row.id}>
          <button type="button" onClick={() => onSelect(row.id)}>
            {row.title}
          </button>
        </li>
      ))}
    </ul>
  );
}

/** Смена sessionKey пересоздаёт subtree: штатный способ «забыть всё черновое». */
export function InterviewBoard({
  sessionKey,
  rows,
}: {
  sessionKey: string;
  rows: Row[];
}): ReactElement {
  const [selected, setSelected] = useState<string | null>(null);
  return <List key={sessionKey} rows={rows.filter((r) => r.id !== selected)} onSelect={setSelected} />;
}
```

Значение `key` меняется — React размонтирует subtree и соберёт заново: фокус, скролл, черновики полей. Это дешевле, чем эффект «при смене id почистить пять стейтов», и не даёт забыть шестое поле.

## Related

- [state.md](state.md) — где держать состояние и как его сбрасывать осознанно
- [effects.md](effects.md) — границы эффекта и cleanup подписок
- [testing.md](testing.md) — тест по ролям: `aria-labelledby` и `aria-expanded` из примера выше — то, по чему ищет `getByRole`
- [../typescript/idioms.md](../../typescript/idioms.md) — union-типы и сужение (для действий редьюсера)
