---
id: ts-file-io
title: "TypeScript: файловый IO (fs/promises, атомарная запись, стримы)"
lang: typescript
min_version: "7.0"
category: snippet
tags: [files, fs, promises, streams, atomic, node]
status: stable
updated: 2026-09-07
---

# Файловый IO (Node.js)

**Когда использовать** — чтение/запись файлов в Node: конфиги, кэши, логи, крупные файлы.
**Когда НЕ использовать** — браузер (нет `fs`): Web Storage / HTTP; Windows-специфику путей — абстрагируйте.

## Код

```ts
import { randomBytes } from "node:crypto";
import { createReadStream, createWriteStream } from "node:fs";
import { promises as fsp } from "node:fs";
import path from "node:path";
import { pipeline } from "node:stream/promises";

/** Атомарная запись: temp-файл в том же каталоге + fsync + rename. */
export async function writeFileAtomic(
  target: string,
  data: string | Uint8Array,
): Promise<void> {
  const dir = path.dirname(target);
  await fsp.mkdir(dir, { recursive: true });

  // Temp рядом с целью: rename в пределах одной ФС атомен.
  const tmp = path.join(
    dir,
    `.${path.basename(target)}.${randomBytes(6).toString("hex")}.tmp`,
  );
  const handle = await fsp.open(tmp, "w");
  try {
    await handle.writeFile(data);
    await handle.sync(); // fsync до rename — данные переживут сбой
    await fsp.rename(tmp, target);
  } catch (err) {
    await fsp.rm(tmp, { force: true });
    throw err;
  } finally {
    await handle.close();
  }
}

/** JSON на границе: парсинг + валидация (zod) — сразу, не «где-то потом». */
export async function readJson<T>(
  file: string,
  parse: (data: unknown) => T,
): Promise<T> {
  const text = await fsp.readFile(file, "utf8");
  return parse(JSON.parse(text));
}

export async function writeJson(file: string, value: unknown): Promise<void> {
  await writeFileAtomic(file, JSON.stringify(value, null, 2) + "\n");
}

/** Крупный файл — стримом, не в память. */
export async function copyFileStreamed(src: string, dest: string): Promise<void> {
  await pipeline(createReadStream(src), createWriteStream(dest));
}

/** Список файлов каталога (без лишних stat). */
export async function listFiles(dir: string, ext = ".md"): Promise<string[]> {
  const entries = await fsp.readdir(dir, { withFileTypes: true });
  return entries
    .filter((e) => e.isFile() && e.name.endsWith(ext))
    .map((e) => path.join(dir, e.name));
}

/** Пример: конфиг с валидацией. */
// import { z } from "zod";
// const ConfigSchema = z.object({ port: z.number().int().positive() });
// const config = await readJson("./config.json", (d) => ConfigSchema.parse(d));
```

## Pitfalls

- **`fsp.writeFile` не атомен**: сбой на полпути = повреждённый файл. Для важных данных — `writeFileAtomic` (temp + fsync + rename).
- **`rename` атомен только в пределах одной файловой системы** (одного mount): temp-файл кладите рядом с целью, не в `/tmp`.
- **Windows**: `fsp.rename` поверх существующего файла падает (`EPERM`/`EEXIST`) — сначала `fsp.rm(target, { force: true })`.
- Крупные файлы — **стримы** (`pipeline`), не `readFile` в память (2 ГБ файла = OOM).
- `fsp.rm` с `recursive: true` для каталогов; без `force` — ошибка на несуществующий путь.
- Ошибки `ENOENT`/`EACCES`/`EEXIST` — обрабатывайте явно, не «перехватывайте всё».
- Пути — только через `path.join`/`path.resolve`, не конкатенация строк (разделители ОС).

## Related

- [async.md](async.md)
- [json.md](json.md)
- [decisions.md](../decisions.md)
