---
id: react-state
title: "React: состояние — редьюсер, выводимое значение, внешний стор, сброс"
lang: react
min_version: "19.3"
category: snippet
tags: [state, usereducer, usestate, derived-state, usesyncexternalstore, store, websocket, reset]
status: stable
updated: 2026-11-24
---

# Состояние: редьюсер, выводимое значение, внешний стор

**Когда использовать** — состояние связано переходами (стадии интервью, шаги, таймер), приходит извне (WebSocket, `localStorage`, медиа-запрос) или требует честного сброса.
**Когда НЕ использовать** — одно значение одного экрана (`useState`), значение, вычисляемое из других (см. ниже), и серверные данные с кэшем (см. [../decisions.md](../decisions.md)).

## Связанные переходы: useReducer

```tsx
import { useReducer, type ReactElement } from "react";

export type Stage = "idle" | "question" | "answer" | "review" | "done";

export type State = {
  stage: Stage;
  attempts: number;
  answer: string;
  error: string | null;
};

export type Action =
  | { type: "start" }
  | { type: "submit"; answer: string }
  | { type: "reveal" }
  | { type: "skip" }
  | { type: "reset" };

const NEXT: Partial<Record<Stage, Stage>> = {
  idle: "question",
  question: "answer",
  answer: "review",
  review: "done",
};

// Переход описан один раз и таблицей, и условием: «разрешено» не разъезжается
// по обработчикам, как это происходит с серией setStage(...) в пяти местах.
export function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "start":
      return { ...state, stage: "question", error: null };
    case "submit": {
      if (state.stage !== "question") return state; // переход вне стадии — игнор
      const answer = action.answer.trim();
      if (!answer) return { ...state, error: "Ответ пустой" };
      return { ...state, answer, attempts: state.attempts + 1, error: null };
    }
    case "reveal":
    case "skip": {
      const next = NEXT[state.stage];
      if (!next) return state;
      return { ...state, stage: next, error: null };
    }
    case "reset":
      return INITIAL;
  }
}

export const INITIAL: State = { stage: "idle", attempts: 0, answer: "", error: null };

export function InterviewFlow({ prompt }: { prompt: string }): ReactElement {
  const [s, dispatch] = useReducer(reducer, INITIAL);

  return (
    <form onSubmit={(e) => { e.preventDefault(); dispatch({ type: "reveal" }); }}>
      <p>{prompt}</p>
      <label>
        Ответ
        <input
          value={s.answer}
          aria-invalid={s.error !== null}
          disabled={s.stage !== "question"}
          onChange={(e) => dispatch({ type: "submit", answer: e.target.value })}
        />
      </label>
      {s.error && <p role="alert">{s.error}</p>}
      <button type="submit" disabled={s.stage !== "question"}>Дальше</button>
      <output>Стадия: {s.stage}, попыток: {s.attempts}</output>
    </form>
  );
}
```

## Выводимое значение не хранится

```tsx
import { useMemo, useState, type ReactElement } from "react";

type Item = { text: string; done: boolean };

export function Todos({ initial }: { initial: Item[] }): ReactElement {
  const [items, setItems] = useState<Item[]>(initial);
  const [query, setQuery] = useState("");

  // Не «отфильтрованный список» в useState: копия рассинхронизируется при первом
  // же внешнем обновлении items и требует эффекта для синхронизации.
  const visible = useMemo(
    () => items.filter((i) => i.text.toLowerCase().includes(query.toLowerCase())),
    [items, query],
  );
  const remaining = items.filter((i) => !i.done).length; // дешёвое — без useMemo

  return (
    <div>
      <input value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Поиск" />
      <p>Осталось: {remaining}, показано: {visible.length}</p>
    </div>
  );
}
```

`useMemo` оправдан на дорогом проходе по большому набору и когда важна идентичность ссылки (мемоизированный ребёнок, подпись эффекта). На `array.filter` десяти элементов — лишний шум.

## Внешний стор: useSyncExternalStore

```tsx
import { useSyncExternalStore, type ReactElement } from "react";

export type Presence = { online: number; lastError: string | null };

/**
 * Стор вне React (сюда пишет WebSocket-колбэк). getSnapshot обязан возвращать
 * стабильный объект: новый объект на каждый вызов = бесконечный цикл перерисовок.
 */
export class PresenceStore {
  private snap: Presence = { online: 0, lastError: null };
  private listeners = new Set<() => void>();

  getSnapshot = (): Presence => this.snap;

  subscribe = (onStoreChange: () => void): (() => void) => {
    this.listeners.add(onStoreChange);
    return () => this.listeners.delete(onStoreChange);
  };

  apply(next: Partial<Presence>): void {
    this.snap = { ...this.snap, ...next };
    for (const l of this.listeners) l();
  }
}

export function usePresence(store: PresenceStore): Presence {
  return useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);
}

export function PresenceBadge({ store }: { store: PresenceStore }): ReactElement {
  const { online, lastError } = usePresence(store);
  return (
    <span role="status">
      {lastError ? "связь потеряна" : `в сети: ${online}`}
    </span>
  );
}
```

Ручная подписка (`useEffect` + `setState`) пропускает сообщения, пришедшие между рендером и установкой подписки, и не совместима с конкурентными обновлениями. `useSyncExternalStore` читает снимок в момент рендера — разрывa нет.

## Сброс

- Один стейт: `setState(INITIAL)`.
- Несколько связанных: `{ type: "reset" }` в редьюсере (выше) — все поля сразу.
- Всё subtree с черновиками: смена `key` ([components.md](components.md)).
- Сброс по смене id экрана — тот же `key`, а не эффект с `setX(«пусто»)`.

## Related

- [effects.md](effects.md) — почему «подписаться в эффекте» хуже `useSyncExternalStore`
- [../database/snippets/redis.md](../../database/snippets/redis.md) — кэш на сервере, когда данных больше, чем влезает в стор
- [../csharp/patterns/state-machine.md](../../csharp/patterns/state-machine.md) — та же таблица переходов на бэкенде: согласуй стадии с сервером
- [../shared/concurrency.md](../../shared/concurrency.md) — гонки при обновлениях из колбэков
