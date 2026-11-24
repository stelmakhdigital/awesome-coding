---
id: react-vite
title: "React: Vite 8 — конфиг, окружение, прокси, чанки (Rolldown)"
lang: react
min_version: "8.3"
category: snippet
tags: [vite, rolldown, env, proxy, build, config, codesplitting, dev-server, toolchain]
status: stable
updated: 2026-11-25
---

# Vite 8: конфиг, окружение, прокси, чанки

**Когда использовать** — настройка сборки фронтенда: прокси на свой API, переменные окружения, разделение чанков, переезд с Vite 6/7.
**Когда НЕ использовать** — SSR-фреймворк с собственным конфигом (Next, React Router, Astro): там Vite спрятан внутри фреймворка, и править надо его секцию.

В 8-й версии бандлер один — Rolldown (вместо esbuild для dev и Rollup для прода), минификатор JS — Oxc, CSS — Lightning CSS. Конфиг-совместимость автоматическая, но часть ключей устарела, а часть удалена — и удалённые не падают, а перестают делать то, что от них ждали.

## Конфиг

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Пути из tsconfig (paths/aliases) — встроенная поддержка, но по умолчанию выключена.
    tsconfigPaths: true,
  },
  server: {
    port: 5173,
    // Старт с чистого localhost без TLS: фронт на 5173, API на 8080, куки не ломаются.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true,
      },
      // WebSocket проксируется тем же префиксом; без ws:true соединение молча
      // уходит в 404, и «руки» доходят до ручного адреса во фронтенде.
      "/ws": { target: "ws://127.0.0.1:8080", ws: true },
    },
    // Логи и ошибки браузера — в терминале, где сидит агент или скрипт.
    // Включается автоматически, когда Vite видит кодинг-агента.
    forwardConsole: true,
  },
  build: {
    // Rolldown: codeSplitting вместо удалённой объектной формы manualChunks.
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: "editor", test: /node_modules\/(monaco-editor|@monaco)/, priority: 20 },
            { name: "vendor", test: /node_modules/, priority: 10 },
          ],
        },
      },
    },
  },
});
```

`changeOrigin` — не про `Origin`-заголовок (его правит `headers`), а про `Host`: без него бэкенд с проверкой `Host` отвечает 400.

## Переменные окружения

Клиентские переменные — только с префиксом `VITE_`; остальное из `.env` в бандл не попадает и в браузере читается как `undefined`. Типы — в `src/vite-env.d.ts`:

```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_WS_URL?: string;
}
```

Дальше — разбор на границе, чтобы опечатка в имени и пустое значение всплывали на старте, а не в момент, когда пользователь нажал кнопку:

```ts
import { z } from "zod";

// vite-env.d.ts — файл без импортов, поэтому там хватает interface.
// Здесь файл модульный: слияние с глобальным ImportMeta — через declare global.
interface Env {
  readonly VITE_API_URL?: string;
  readonly VITE_WS_URL?: string;
}
declare global {
  interface ImportMeta {
    readonly env: Env;
  }
}

const Schema = z.object({
  apiUrl: z.url(),
  wsUrl: z.url().default("ws://127.0.0.1:8080/ws"),
});

export type AppConfig = z.infer<typeof Schema>;

export function readConfig(): AppConfig {
  const parsed = Schema.safeParse({
    apiUrl: import.meta.env.VITE_API_URL,
    wsUrl: import.meta.env.VITE_WS_URL,
  });
  if (!parsed.success) {
    // Ошибка на старте лучше «серого экрана» через минуту: имя поля указывает,
    // какую переменную ждать в .env.example.
    const keys = parsed.error.issues.map((i) => i.path.join(".")).join(", ");
    throw new Error(`некорректное окружение: ${keys || "VITE_API_URL"}`);
  }
  return parsed.data;
}
```

## Миграция с Vite 6/7

| Было | Стало | Что происходит, если не поменять |
|---|---|---|
| `build.rollupOptions.output.manualChunks: { vendor: [...] }` | `build.rolldownOptions.output.codeSplitting.groups` | объектная форма удалена: чанки делятся не по вашему плану, размер бандла «странно» меняется, ошибки нет |
| `build.rollupOptions.output.manualChunks: fn` | то же | deprecated; работает, но уйдёт |
| `esbuild: { ... }` (верхний уровень) | `oxc: { ... }` (`jsx: "automatic"` → `jsx: { runtime: "automatic" }`) | автоконвертация есть; `banner`/`footer` — только своим плагином с `transform` |
| `optimizeDeps.esbuildOptions` | `optimizeDeps.rolldownOptions` | `define` → `transform.define`, `loader` → `moduleTypes`, `supported` — не поддерживается |
| `build.minify: "esbuild"` | дефолт — Oxc-минификатор | требует `esbuild` в devDependencies, если возврат; `mangleProps` недоступен |
| дефолтный CSS-минификатор | Lightning CSS | правила, которые esbuild проглатывал, теперь могут быть перебиты или отброшены: проверять `dist/assets/*.css`, а не глазами |
| `rollupOptions.watch.chokidar` | `rolldownOptions.watch.watcher` | ошибка конфига |

Мигрировать в два шага: сначала `rolldown-vite` на 7-й линии (отделяет проблемы бандлера от проблем Vite), потом 8. Сравнение — по составу `dist/assets` до и после, а не по «сборка прошла».

## dev-сервер и агент

`server.forwardConsole` пересылает `console.log`/`console.error` браузера в терминал dev-сервера. Для работы из терминала (агент, CI-скрипт, ssh-сессия) это способ увидеть клиентскую ошибку, не открывая окно браузера: `curl` ответа HTML-страницы таких ошибок не даёт вовсе.

`vite build` + `vite preview` в CI дешевле, чем «собрать и залить на прод» — на preview ловятся сломанные относительные пути и отсутствующие переменные окружения.

## Related

- [heavy-widget.md](heavy-widget.md) — зачем отдельный чанк на редактор и холст
- [decisions.md](../decisions.md) — обновление тулчейна: порядок и тихие поломки
- [testing.md](testing.md) — Vitest использует тот же конфиг и `vite` как peer-зависимость
- [../cicd/snippets/docker.md](../../cicd/docker.md) — многоэтапный образ фронтенда (build → nginx/Caddy)
- [../shared/configuration.md](../../shared/configuration.md) — общие правила конфигурации и секретов
