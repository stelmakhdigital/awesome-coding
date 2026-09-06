#!/usr/bin/env node
/**
 * Валидация mermaid-блоков всех .md репозитория.
 *
 * Собирает блоки ```mermaid и парсит их через mermaid.parse().
 * Запуск: make validate-mermaid (предварительно: cd tools && npm install).
 * Exit code: 0 — всё ок, 1 — найдены ошибки синтаксиса.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { JSDOM } from "jsdom";

const ROOT = new URL("..", import.meta.url).pathname;

// mermaid требует DOM — готовим его ДО импорта пакета.
const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", {
  pretendToBeVisual: true,
});
globalThis.window = dom.window;
globalThis.document = dom.window.document;
Object.defineProperty(globalThis, "navigator", {
  value: dom.window.navigator,
  configurable: true,
});
globalThis.requestAnimationFrame = (cb) => setTimeout(cb, 16);
globalThis.cancelAnimationFrame = (id) => clearTimeout(id);

const mermaid = (await import("mermaid")).default;

function* mdFiles(dir) {
  for (const name of readdirSync(dir)) {
    if (name === ".git" || name === "node_modules") continue;
    const full = join(dir, name);
    const st = statSync(full);
    if (st.isDirectory()) yield* mdFiles(full);
    else if (name.endsWith(".md")) yield full;
  }
}

const BLOCK_RE = /```mermaid\r?\n([\s\S]*?)```/g;

let total = 0;
let failed = 0;
for (const file of mdFiles(ROOT)) {
  const text = readFileSync(file, "utf8");
  const rel = relative(ROOT, file);
  for (const match of text.matchAll(BLOCK_RE)) {
    const code = match[1].trim();
    if (!code) continue;
    total += 1;
    const line = text.slice(0, match.index).split("\n").length;
    try {
      await mermaid.parse(code);
    } catch (err) {
      failed += 1;
      const msg = String(err.message ?? err).split("\n").slice(0, 3).join(" | ");
      console.log(`  - ${rel}:${line}: ${msg}`);
    }
  }
}

if (failed > 0) {
  console.log(`\n[mermaid] ${failed} из ${total} блоков не прошли парсинг`);
  process.exit(1);
}
console.log(`[mermaid] ok: ${total} блоков`);
