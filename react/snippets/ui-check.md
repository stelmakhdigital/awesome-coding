---
id: react-ui-check
title: "React: проверка вёрстки числами — без скриншотов и vision-модели"
lang: react
category: snippet
min_version: "19.3"
tags: [browser, layout, getComputedStyle, accessibility, contrast, tap-target, verification, agent]
status: stable
updated: 2026-11-25
---

# Проверка вёрстки числами: без скриншотов и vision-модели

**Когда использовать** — нужно проверить или починить разметку, не глядя на картинку: агент в терминале, CI без браузера с окном, отчёт «кнопки наезжают друг на друга» словами. Работает в консоли браузера, в `page.evaluate` у Playwright и в dev-сервере Vite с `forwardConsole`.
**Когда НЕ использовать** — оценивать «красиво» (вкус остаётся человеку) и проверять это в jsdom: layout там не считается, `getBoundingClientRect` возвращает нули, и тест «не наезжает» пройдёт всегда.

## Измерения

```tsx
export type Issue = { rule: string; where: string; value: string };

const px = (v: string): number => Number.parseFloat(v) || 0;

/** Кликабельность: минимум 44 px по меньшей стороне (мобильные ориентировки). */
export function checkTapTargets(root: HTMLElement): Issue[] {
  const out: Issue[] = [];
  const nodes = root.querySelectorAll<HTMLElement>("button, a[href], input, [role='button']");
  for (const el of nodes) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) {
      out.push({ rule: "нулевой размер", where: describe(el), value: `${r.width}x${r.height}` });
      continue;
    }
    const min = Math.min(r.width, r.height);
    if (min < 44) out.push({ rule: "мишень < 44px", where: describe(el), value: `${Math.round(min)}px` });
  }
  return out;
}

/** Переполнение: текст вылез за границу или срезан — частая причина «всё съехало» после правки. */
export function checkOverflow(root: HTMLElement): Issue[] {
  const out: Issue[] = [];
  for (const el of [root, ...root.querySelectorAll<HTMLElement>("*")]) {
    const style = getComputedStyle(el);
    if (style.overflow === "visible") continue;
    const dx = el.scrollWidth - el.clientWidth;
    const dy = el.scrollHeight - el.clientHeight;
    if (dx > 1 || dy > 1) {
      out.push({ rule: "обрезано содержимое", where: describe(el), value: `+${dx}x+${dy}` });
    }
  }
  return out;
}

/** Наложение соседних кнопок: один и тот же пиксель под двумя целями. */
export function checkOverlap(root: HTMLElement): Issue[] {
  const targets = [...root.querySelectorAll<HTMLElement>("button, a[href]")].map((el) => ({
    el,
    r: el.getBoundingClientRect(),
  }));
  const out: Issue[] = [];
  for (let i = 0; i < targets.length; i += 1) {
    for (let j = i + 1; j < targets.length; j += 1) {
      const a = targets[i];
      const b = targets[j];
      if (!a || !b) continue;
      const x = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
      const y = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
      if (x > 4 && y > 4) {
        out.push({ rule: "наложение", where: `${describe(a.el)} / ${describe(b.el)}`, value: `${Math.round(x)}x${Math.round(y)}` });
      }
    }
  }
  return out;
}

/** Контраст текста по WCAG: 4.5 для обычного текста, 3 для крупного. */
export function checkContrast(root: HTMLElement, largePx = 18): Issue[] {
  const out: Issue[] = [];
  for (const el of root.querySelectorAll<HTMLElement>("p, span, a, button, label, h1, h2, h3")) {
    const style = getComputedStyle(el);
    const own = [...el.childNodes].some((n) => n.nodeType === Node.TEXT_NODE && n.textContent?.trim());
    if (!own) continue; // проверяем только собственный текст элемента, не наследуемый
    const fg = parseColor(style.color);
    const bg = effectiveBackground(el);
    if (!fg || !bg) continue;
    const ratio = contrast(fg, bg);
    const need = px(style.fontSize) >= largePx || Number(style.fontWeight) >= 700 ? 3 : 4.5;
    if (ratio < need) {
      out.push({ rule: "контраст", where: describe(el), value: `${ratio.toFixed(2)} < ${need}` });
    }
  }
  return out;
}

function describe(el: Element): string {
  const id = el.id ? `#${el.id}` : "";
  const cls = el.classList.length > 0 ? `.${[...el.classList].join(".")}` : "";
  const text = (el.textContent ?? "").trim().slice(0, 24);
  return `${el.tagName.toLowerCase()}${id}${cls}${text ? ` «${text}»` : ""}`;
}

function parseColor(v: string): [number, number, number] | null {
  const m = /rgba?\(([^)]+)\)/.exec(v);
  if (!m) return null;
  const parts = (m[1] ?? "").split(/[\s,\/]+/).map(Number).filter((n) => !Number.isNaN(n));
  const [r, g, b, a] = parts;
  if (r === undefined || g === undefined || b === undefined) return null;
  if (a === 0) return null; // полностью прозрачный текст не читаем
  return [r, g, b];
}

function effectiveBackground(el: Element): [number, number, number] | null {
  for (let node: Element | null = el; node; node = node.parentElement) {
    const c = parseColor(getComputedStyle(node).backgroundColor);
    if (c) return c;
  }
  return null;
}

function luminance(c: [number, number, number]): number {
  const ch = c.map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  const [r, g, b] = ch;
  return 0.2126 * (r ?? 0) + 0.7152 * (g ?? 0) + 0.0722 * (b ?? 0);
}

function contrast(a: [number, number, number], b: [number, number, number]): number {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return ((l1 ?? 0) + 0.05) / ((l2 ?? 0) + 0.05);
}
```

## Как это читать

Функции выше — обычный модуль, их можно импортировать и вызывать из `page.evaluate`. Точка входа одна:

```text
// в консоли браузера (или в page.evaluate у Playwright):
> audit()
[{ rule: "мишень < 44px", where: "button.icon «×»", value: "28px" },
 { rule: "обрезано содержимое", where: "div.card.title «Длинный заголовок»", value: "+38x+0" }]
```

- Отчёт — список с числами. «Кнопка маленькая» превращается в «28px против 44px», и правка проверяема: стало `>= 44`.
- Порядок правок по признаку: сначала обрезанное содержимое (ломает контент), потом наложения (ломает нажатия), потом мишени и контраст (ломает доступность).
- `forwardConsole: true` в Vite (см. [vite.md](vite.md)) печатает эти строки в терминале: результат измерений доходит до того, кто правит код, без окна браузера.
- Перед каждой серией замеров — одна и та же ширина окна (например 390 и 1280). Сравнение «до/после» на разных ширинах бессмысленно: responsive-правки всё перепишут.

## Related

- [testing.md](testing.md) — поведение в jsdom; размеры — здесь
- [rules.md](../rules.md) — доступность: откуда берутся 44 px и 4.5
- [../shared/code-review.md](../../shared/code-review.md) — чем измерять, прежде чем спорить о вкусах
