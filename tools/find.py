#!/usr/bin/env python3
"""Поиск по каталогу: нормализация запроса, алиасы, ранжирование.

Общая логика для `tools/search.py` (CLI) и `tools/mcp_server.py` (MCP). Каталог
`index/*.yaml` — источник истины; текст записей не читается (иначе поиск
превращается в grep по 170 файлам, что агент может сделать и сам).

Ранжирование нужно потому, что вывод без порядка заставляет агента читать первые
пять записей подряд, когда первая — точное совпадение тега.

Порядок оценки (выше = ближе к запросу):
  100 тег совпал целиком
   80 запись названа в index/aliases.yaml под этим словом
   70 id совпал целиком
   60 тег содержит запрос как подстроку
   40 запрос в названии
   20 id содержит запрос
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml  # noqa: F401  — нужен tools/ac.py
except ImportError:
    print("ОШИБКА: нужен PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ac import INDEX_DIR, index_entries  # noqa: E402

ALIASES_FILE = INDEX_DIR / "aliases.yaml"
FIELDS = ("id", "title", "path", "tags", "status", "verified", "updated")


def normalize(term: str) -> str:
    """Каноническая форма тега/алиаса: «Rate Limit», «rate_limit» -> «rate-limit»."""
    return " ".join(term.split()).lower().replace("_", "-").replace(" ", "-")


def forms(query: str) -> list[str]:
    """Формы запроса: раздельно, через дефис и слитно.

    Одно и то же название в заголовке пишется «HTTP client», в тегах —
    «http-client», а хуки React называются слитно — «useeffect». Оставить одну
    форму — значит потерять треть совпадений, поэтому пробираются три и берётся
    лучшая оценка.
    """
    spaced = " ".join(query.split()).lower()
    if not spaced:
        return []
    hyphen = spaced.replace("_", "-").replace(" ", "-")
    glued = hyphen.replace("-", "")
    return list(dict.fromkeys([spaced, hyphen, glued]))


def aliases() -> dict[str, list[str]]:
    """index/aliases.yaml: слово -> id записей. Файл опционален."""
    if not ALIASES_FILE.exists():
        return {}
    data = yaml.safe_load(ALIASES_FILE.read_text(encoding="utf-8")) or {}
    return {normalize(k): [str(i) for i in v]
            for k, v in (data.get("aliases") or {}).items()}


def score(entry: dict, queries: list[str]) -> int:
    tags = [normalize(str(t)) for t in entry.get("tags") or []]
    rid = normalize(str(entry.get("id", "")))
    title = " ".join(str(entry.get("title", "").lower()).split())
    best = 0
    for q in queries:
        if q in tags:
            s = 100
        elif q == rid:
            s = 70
        elif any(q in t for t in tags):
            s = 60
        elif q in title:
            s = 40
        elif q in rid:
            s = 20
        else:
            s = 0
        best = max(best, s)
    return best


def find(query: str, section: str | None = None) -> list[dict]:
    """Записи, отсортированные по близости к запросу (при равных — по id).

    section — префикс пути («go», «database/snippets»), фильтр применяется до
    ранжирования.
    """
    queries = forms(query or "")
    wanted = {i for q in queries for i in aliases().get(q, ())}
    hits: list[dict] = []
    for _, entry in index_entries():
        path = str(entry.get("path", ""))
        if section and not path.startswith(section.strip("/") + "/"):
            continue
        s = score(entry, queries) if queries else 0
        if str(entry.get("id", "")) in wanted:
            s = max(s, 80)
        if queries and s == 0:
            continue
        hits.append({**{k: entry.get(k) for k in FIELDS}, "score": s})
    hits.sort(key=lambda h: (-h["score"], str(h["id"])))
    return hits
