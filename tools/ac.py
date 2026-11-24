#!/usr/bin/env python3
"""Общие утилиты туллинга awesome-coding.

Один разбор формата записей на весь тулинг: frontmatter, обход контент-файлов,
обход каталога `index/`, поиск код-блоков. Используют:
  validate.py       — проверки репозитория
  search.py         — поиск по каталогу
  check_stale.py    — аудит свежести
  verify_snippets.py — прогон код-блоков через тулчейны

Правила формата — docs/FORMAT.md.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("ОШИБКА: нужен PyYAML: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = ROOT / "index"
MANIFEST = INDEX_DIR / "manifest.yaml"
# Файлы каталога, которые не являются разделом записей.
INDEX_AUX = {"manifest.yaml", "aliases.yaml"}

# Файлы и каталоги, которым frontmatter НЕ требуется.
NO_FRONTMATTER = {"README.md", "AGENTS.md", "CHANGELOG.md"}
NO_FRONTMATTER_DIRS = {"docs", "skills"}
SKIP_DIRS = {".git", "node_modules"}

# Языки, код которых проверяется компилятором/интерпретатором. Декларативные
# (dockerfile, yaml, protobuf) и компилируемые только в Editor (hlsl) сюда не входят.
CODE_LANGS = {"go", "c", "csharp", "kotlin", "python", "bash", "sh",
              "ts", "tsx", "js", "sql"}
CODE_FENCE_RE = re.compile(r"^```([a-zA-Z]+)[ \n]", re.M)


def parse_frontmatter(path: Path) -> dict | None:
    """Frontmatter как dict или None (файл без него). yaml.YAMLError не перехватывается."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    data = yaml.safe_load(text[4:end])
    return data if isinstance(data, dict) else None


def needs_frontmatter(path: Path) -> bool:
    if path.name in NO_FRONTMATTER:
        return False
    return not any(part in NO_FRONTMATTER_DIRS for part in path.parts)


def all_md_files() -> list[Path]:
    """Все .md репозитория (кроме служебных каталогов)."""
    return sorted(p for p in ROOT.rglob("*.md") if not (SKIP_DIRS & set(p.parts)))


def content_files() -> list[Path]:
    """Контент-файлы: те, что обязаны иметь frontmatter."""
    return [p for p in all_md_files() if needs_frontmatter(p)]


def index_files() -> list[Path]:
    """Секционные файлы каталога: index/<section>.yaml. Шапка и алиасы — не разделы
    (manifest.yaml читается отдельно, aliases.yaml — справочник поиска, не записи)."""
    return sorted(p for p in INDEX_DIR.glob("*.yaml") if p.name not in INDEX_AUX)


def index_entries() -> list[tuple[Path, dict]]:
    """Все записи каталога: (секция-путь, entry). Секция = `<section>/<ключ>`,
    напр. `go/snippets` или `csharp/rule_set`."""
    entries: list[tuple[Path, dict]] = []

    def walk(node, section: Path):
        if isinstance(node, dict):
            if "path" in node and "id" in node:
                entries.append((section, node))
            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    walk(value, section / str(key))
        elif isinstance(node, list):
            for item in node:
                walk(item, section)

    for mf in index_files():
        try:
            data = yaml.safe_load(mf.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue  # невалидный YAML отмечает validate.py
        if not isinstance(data, dict):
            continue
        for key, value in data.items():
            if key in ("version", "updated", "languages"):
                continue
            walk(value, Path(mf.stem) / str(key))
    return entries


def code_fences(text: str) -> set[str]:
    """Языки код-блоков, только из CODE_LANGS (```<lang> в начале строки)."""
    return {lang.lower() for lang in CODE_FENCE_RE.findall(text)} & CODE_LANGS


def fence_blocks(text: str, langs: set[str] | None = None) -> list[tuple[str, str]]:
    """Код-блоки записи: [(lang, code), ...]. langs — фильтр; None = все языки."""
    out: list[tuple[str, str]] = []
    lang: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        if lang is None:
            m = re.match(r"^```([a-zA-Z]+)[ \n]*$", line)
            if m and (langs is None or m.group(1).lower() in langs):
                lang = m.group(1).lower()
                buf = []
            continue
        if line.startswith("```"):
            out.append((lang, "\n".join(buf).strip("\n")))
            lang = None
            continue
        buf.append(line)
    return out
