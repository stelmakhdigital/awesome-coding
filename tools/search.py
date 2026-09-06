#!/usr/bin/env python3
"""Поиск записей в index/manifest.yaml по тегу или подстроке в названии.

Использование:
  python3 tools/search.py async          # точное совпадение тега
  python3 tools/search.py "http client"  # подстрока в title/tags (регистр не важен)

Вывод: `id — title — path` по одной строке на запись.
Exit code: 0 — найдено (или нет, это информационно), 2 — ошибка.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "index" / "manifest.yaml"


def entries() -> list[dict]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))

    def walk(node):
        if isinstance(node, dict):
            if "id" in node and "path" in node:
                yield node
            for value in node.values():
                if isinstance(value, (dict, list)):
                    yield from walk(value)
        elif isinstance(node, list):
            for item in node:
                yield from walk(item)

    yield from walk(data)


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        print(__doc__.strip(), file=sys.stderr)
        return 2
    query = sys.argv[1].strip().lower()

    found = 0
    for entry in entries():
        tags = [str(t).lower() for t in entry.get("tags", [])]
        title = str(entry.get("title", "")).lower()
        # Точное совпадение тега ИЛИ подстрока в тегах/названии.
        if query in tags or query in title or any(query in t for t in tags):
            found += 1
            print(f"{entry['id']} — {entry.get('title', '')} — {entry.get('path', '')}")
    if found == 0:
        print(f"ничего не найдено по запросу: {sys.argv[1]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
