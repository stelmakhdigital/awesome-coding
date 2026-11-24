---
id: react-testing
title: "React: тесты — Vitest 5 + Testing Library по поведению"
lang: react
min_version: "19.3"
category: snippet
tags: [testing, vitest, jsdom, testing-library, user-event, a11y, mocks, timers]
status: stable
updated: 2026-11-24
---

# Тесты: Vitest 5 + Testing Library по поведению

**Когда использовать** — любой код, который пользователь может сломать руками: поля, кнопки, состояния загрузки и ошибки, доступность.
**Когда НЕ использовать** — проверка размеров, наездов и реальной сетки CSS (jsdom layout не считает, [ui-check.md](ui-check.md)) и чистых функций, которым не нужен DOM (их тестят в node-окружении, без jsdom).

## Настройка jsdom

```tsx
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom не реализует то, чем пользуется layout-код. Заглушки ставятся один раз
// в настройке, а не по `if (typeof window)` внутри компонента.
if (!window.matchMedia?.("x")?.addEventListener) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
    }) as unknown as MediaQueryList;
}

globalThis.ResizeObserver = class {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
} as unknown as typeof ResizeObserver;

afterEach(() => cleanup()); // RTL делает это сам, если globals: true; при импортах — вручную

// В Vitest 5 clearMocks по умолчанию true: перед каждым тестом сбрасываются
// записанные вызовы (mock.calls), но НЕ реализация. За «вернуть другое» отвечают
// mockReset (сброс реализации) и mockRestore (вернуть настоящий метод).
void vi.clearAllMocks();
```

`vite` в Vitest 5 — peer-зависимость: на yarn её надо держать в `devDependencies` явно, иначе тесты не поднимают сервер модулей.

## Тест по поведению

```tsx
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { useState, type ReactElement } from "react";

function SaveButton({ onSave }: { onSave: () => Promise<void> }): ReactElement {
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        setBusy(true);
        setFailed(false);
        onSave()
          .catch(() => setFailed(true))
          .finally(() => setBusy(false));
      }}
    >
      <button type="submit" disabled={busy} aria-busy={busy}>
        {busy ? "Сохраняем…" : "Сохранить"}
      </button>
      {failed && <p role="alert">Не сохранилось</p>}
    </form>
  );
}

describe("SaveButton", () => {
  it("сохраняет по клику", async () => {
    const onSave = vi.fn(async () => {});
    render(<SaveButton onSave={onSave} />);

    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("показывает ошибку и возвращает кнопку", async () => {
    const onSave = vi.fn(async () => {
      throw new Error("503");
    });
    render(<SaveButton onSave={onSave} />);

    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    // findBy* вместо waitFor + getBy*, когда ждём появления элемента
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Не сохранилось");
    // Без jest-dom: обычное свойство элемента, а не матчер toBeEnabled()
    expect(screen.getByRole("button", { name: "Сохранить" }).hasAttribute("disabled")).toBe(false);
  });
});

describe("форма поля", () => {
  function Field(): ReactElement {
    const [v, setV] = useState("");
    return (
      <form>
        <label htmlFor="nick">Ник</label>
        <input id="nick" value={v} aria-invalid={v.length < 3} onChange={(e) => setV(e.target.value)} />
      </form>
    );
  }

  it("печатается и связан с подписью", async () => {
    render(<Field />);
    const input = screen.getByRole("textbox", { name: "Ник" }); // имя из <label htmlFor>

    await userEvent.type(input, "арка");

    expect((input as HTMLInputElement).value).toBe("арка");
    const form = input.closest("form");
    expect(form).not.toBeNull();
    await within(form as HTMLElement).findByLabelText("Ник");
  });
});
```

## Правила, которые держат тесты

- Искать по роли и имени (`getByRole("button", { name: "Сохранить" })`). Доступное имя — то, что читает скринридер; тест на `data-testid` проходит и при недоступной кнопке.
- `userEvent`, не `fireEvent`: первый эмулирует реальные шаги (фокус, pointer events), второй — один синтезированный вызов.
- `await` на каждом действии и `findBy*`/`waitFor` на ожидания. Цикл «поспать и проверить» даёт flaky вместо ответа.
- Тест описывает один сценарий: «сохраняет», «показывает ошибку», «блокирует на время полёта» — три теста, а не один с тремя ожиданиями разного уровня.
- Не мокировать свои компоненты. Мок `fetch`/`WebSocket` — да (`vi.fn`, stub-класс), дочерний `Panel` — нет.

## Ловушки Vitest 5

| Что | Эффект | Что делать |
|---|---|---|
| `clearMocks: true` по умолчанию | сброс записанных вызовов перед каждым тестом | не полагаться на «накопленные вызовы» из `beforeEach`; за реализацию — `mockReset`/`mockRestore` |
| `vi.mock` внутри `describe`/функции | ошибка вместо предупреждения | `vi.mock` — только на верхнем уровне модуля |
| `-t` матчится по полному имени через `" > "` | привычный `vitest -t "печатается"` может не найти тест | имя с цепочкой: `-t "форма поля > печатается"` |
| `vite` — peer-зависимость | yarn: «Cannot find package 'vite'` | `vite` в `devDependencies` |
| Vitest UI | требует аутентифицированный URL | открывать ссылку, которую печатает процесс, а не `localhost:5173/__vitest__` в лоб |
| Автомок в browser-режиме | экспорт без фабрики теперь `undefined` | давать фабрику явно |

## Related

- [ui-check.md](ui-check.md) — что проверяется только в настоящем браузере
- [rules.md](../rules.md) — доступность: без неё нечего искать по роли
- [../shared/testing.md](../../shared/testing.md) — общие правила тестов, пирамиды, flaky
- [../typescript/snippets/testing.md](../../typescript/snippets/testing.md) — тесты чистого TS-кода
