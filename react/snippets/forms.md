---
id: react-forms
title: "React: форма — контролируемые поля, useActionState, серверные ошибки"
lang: react
min_version: "19.3"
category: snippet
tags: [forms, useactionstate, useformstatus, validation, zod, a11y, submit, abort]
status: stable
updated: 2026-11-24
---

# Форма: контролируемые поля, статус отправки, серверные ошибки

**Когда использовать** — форма с несколькими полями, валидацией и отправкой на сервер, включая серверные ошибки по полям.
**Когда НЕ использовать** — один `input` с кнопкой (хватит контролируемого поля), многошаговый мастер с шагами-URL (там редьюсер + `searchParams`, [../decisions.md](../decisions.md)), таблицы с тысячами ячеек (нужна специализированная библиотека).

## Форма целиком

```tsx
// useActionState — из react; useFormStatus — из react-dom (там живёт контекст <form>).
import { useActionState, type ReactElement } from "react";
import { useFormStatus } from "react-dom";
import { z } from "zod";

export const CandidateSchema = z.object({
  name: z.string().min(2, "Имя короче двух символов").max(80),
  email: z.email("Проверьте адрес"),
  years: z.coerce.number().int().min(0).max(50),
  agree: z.literal(true, { error: "Нужно согласие" }),
});

export type Candidate = z.infer<typeof CandidateSchema>;
export type FieldErrors = Partial<Record<keyof Candidate, string>>;

/** Ошибки zod → карта по полям: UI показывает их у полей, а не списком внизу. */
export function fieldErrors(err: z.ZodError): FieldErrors {
  const out: FieldErrors = {};
  for (const issue of err.issues) {
    const key = String(issue.path[0] ?? "") as keyof Candidate;
    if (!(key in out)) out[key] = issue.message; // первая ошибка поля важнее остальных
  }
  return out;
}


type FormState = { errors: FieldErrors; message: string | null };

const IDLE: FormState = { errors: {}, message: null };

// Порядок аргументов action: (предыдущее состояние, данные формы). PREV не читается —
// состояние целиком строится из ответа, — но второй аргумент обязан быть вторым.
async function send(_prev: FormState, payload: FormData): Promise<FormState> {
  const parsed = CandidateSchema.safeParse({
    name: payload.get("name") ?? "",
    email: payload.get("email") ?? "",
    years: payload.get("years") ?? "",
    // чекбокс отсутствует в FormData, когда снят —.literal ругается сам
    agree: payload.get("agree") === "on",
  });
  if (!parsed.success) return { errors: fieldErrors(parsed.error), message: null };

  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), 8_000);
  try {
    const res = await fetch("/api/candidates", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(parsed.data),
      signal: ac.signal,
    });
    if (res.status === 409) {
      // Серверная ошибка по полю приезжает кодом, а не текстом: текст — на клиенте.
      return { errors: { email: "Такой адрес уже зарегистрирован" }, message: null };
    }
    if (!res.ok) return { errors: {}, message: `Сервер ответил ${res.status}` };
    return IDLE;
  } catch {
    return { errors: {}, message: ac.signal.aborted ? "Превышено время ожидания" : "Нет связи" };
  } finally {
    clearTimeout(timer);
  }
}

function SubmitButton(): ReactElement {
  // Статус полёта берётся из контекста формы: своего useState для кнопки не нужно.
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending} aria-busy={pending}>
      {pending ? "Отправляем…" : "Отправить"}
    </button>
  );
}

export function CandidateForm(): ReactElement {
  const [state, action] = useActionState<FormState, FormData>(send, IDLE);

  const field = (name: keyof typeof IDLE.errors, label: string, type = "text"): ReactElement => (
    <p>
      <label htmlFor={name}>{label}</label>
      <input
        id={name}
        name={name}
        type={type}
        aria-invalid={state.errors[name] !== undefined}
        aria-describedby={state.errors[name] ? `${name}-error` : undefined}
      />
      {state.errors[name] && (
        <span id={`${name}-error`} role="alert">
          {state.errors[name]}
        </span>
      )}
    </p>
  );

  return (
    <form action={action} noValidate>
      {field("name", "Имя")}
      {field("email", "Почта", "email")}
      {field("years", "Опыт, лет", "number")}
      {state.message && <p role="alert">{state.message}</p>}
      <SubmitButton />
    </form>
  );
}
```

## Что здесь важно

- `noValidate` — своя валидация и свои сообщения; браузерные всплывашки не перевести и не стилизовать, а порядок полей у них свой.
- `useActionState` держит «отправка/ошибка» и обновляет состояние после `await`: ручной `setBusy(true)`/`setBusy(false)` в `onClick` забывает случай, когда компонент размонтирован.
- `useFormStatus` читается только внутри `form` и только из дочернего компонента — в том же, где рендерится `form`, он всегда даёт `false`.
- Разбор — на границе (`safeParse`), а не «там, где используем»: `payload.get("years")` — строка или `null`, и `Number(null)` даёт 0.
- Ошибки — по полям плюс общая строка на случай, когда поля не при чём (500, таймаут).
- `aria-describedby` + `role="alert"`: скринридер объявляет ошибку, а зрячий пользователь видит её у того же поля.
- Отправка повторяемая? На сервере — идемпотентный ключ или уникальный индекс; кнопка `disabled` от двойного клика не защищает (Enter посылает форму и до `disabled` дело доходит).

## Related

- [state.md](state.md) — локальное состояние полей, когда редьюсер избыточен
- [testing.md](testing.md) — тест формы через `userEvent` и `getByRole`
- [../shared/api-design.md](../../shared/api-design.md) — коды ошибок и форма ответа сервера
- [../typescript/idioms.md](../../typescript/idioms.md) — `unknown` на границе и сужение через схему
