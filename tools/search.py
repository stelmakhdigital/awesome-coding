#!/usr/bin/env python3
"""Поиск записей в каталоге index/*.yaml по тегу, названию или алиасу.

Использование:
  python3 tools/search.py async          # тег, подстрока тега/названия
  python3 tools/search.py "rate limit"   # пробелы и подчёркивания = дефис
  python3 tools/search.py upsert         # по alias из index/aliases.yaml

Вывод: `id — title — path`, по строке на запись, от самых близких к запросу;
не больше 10 строк — остальные сворачиваются в «+N ещё, уточните запрос».
Порядок и правила — tools/find.py (та же логика у tools/mcp_server.py).
Exit code: 0 — всегда (пустой результат информационный), 2 — ошибка.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from find import cap, find  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2 or not sys.argv[1].strip():
        print(__doc__.strip(), file=sys.stderr)
        return 2

    hits = find(sys.argv[1])
    if not hits:
        print(f"ничего не найдено по запросу: {sys.argv[1]!r}")
        return 0
    shown, tail = cap(hits)
    for hit in shown:
        print(f"{hit['id']} — {hit['title']} — {hit['path']}")
    if tail:
        print(tail)
    return 0


if __name__ == "__main__":
    sys.exit(main())
