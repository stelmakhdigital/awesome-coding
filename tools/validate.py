#!/usr/bin/env python3
"""Валидатор awesome-coding: frontmatter, manifest, ссылки.

Проверки:
  frontmatter — YAML frontmatter всех .md: обязательные поля, допустимые
                значения, уникальные id, формат полей.
  manifest    — index/manifest.yaml: пути существуют, все контент-файлы
                есть в manifest, id/title/status совпадают с frontmatter.
  links       — относительные markdown-ссылки указывают на существующие файлы.

Использование:
  python3 tools/validate.py [--check frontmatter|manifest|links|all]

Зависимости: Python 3.9+, PyYAML (pip install pyyaml).
Exit code: 0 — всё ок, 1 — найдены проблемы.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ОШИБКА: нужен PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "index" / "manifest.yaml"

# Файлы, которым frontmatter НЕ требуется.
NO_FRONTMATTER = {
    "README.md",  # любой README (индексы разделов)
    "AGENTS.md",
}
NO_FRONTMATTER_DIRS = {"docs"}

ALLOWED_LANGS = {
    "go", "typescript", "javascript", "python", "c", "bash",
    "csharp", "kotlin", "unity", "shared", "database", "messaging", "cicd",
}
ALLOWED_CATEGORIES = {"concept", "rule-set", "idioms", "decisions", "snippet", "pattern"}
ALLOWED_STATUS = {"stable", "experimental", "deprecated"}
ID_PREFIXES = (
    "go", "ts", "js", "py", "c", "bash", "csharp", "kotlin", "unity",
    "shared", "ddd", "arch", "database", "messaging", "cicd",
)
REQUIRED_FIELDS = ("id", "title", "lang", "min_version", "category", "tags", "status", "updated")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def parse_frontmatter(path: Path) -> dict | None:
    """Вернуть dict frontmatter или None (файл без frontmatter)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    raw = text[4:end]
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        return None
    return data


def all_md_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md") if ".git" not in p.parts)


def needs_frontmatter(path: Path) -> bool:
    if path.name in NO_FRONTMATTER:
        return False
    if any(part in NO_FRONTMATTER_DIRS for part in path.parts):
        return False
    return True


def check_frontmatter() -> list[str]:
    issues: list[str] = []
    seen_ids: dict[str, Path] = {}
    for path in all_md_files():
        rel = path.relative_to(ROOT)
        try:
            fm = parse_frontmatter(path)
        except yaml.YAMLError as e:
            issues.append(f"{rel}: невалидный YAML в frontmatter: {str(e).splitlines()[0]}")
            continue
        if fm is None:
            if needs_frontmatter(path):
                issues.append(f"{rel}: нет frontmatter (обязателен для контент-файлов)")
            continue
        for field in REQUIRED_FIELDS:
            if field not in fm:
                issues.append(f"{rel}: нет поля '{field}'")
        fid = fm.get("id")
        if isinstance(fid, str):
            if not ID_RE.match(fid):
                issues.append(f"{rel}: id '{fid}' не в kebab-case")
            elif not fid.startswith(ID_PREFIXES):
                issues.append(f"{rel}: id '{fid}' не начинается с известного префикса")
            elif fid in seen_ids:
                issues.append(f"{rel}: дубликат id '{fid}' (уже в {seen_ids[fid].relative_to(ROOT)})")
            else:
                seen_ids[fid] = path
        lang = fm.get("lang")
        if lang is not None and lang not in ALLOWED_LANGS:
            issues.append(f"{rel}: lang '{lang}' не в списке {sorted(ALLOWED_LANGS)}")
        cat = fm.get("category")
        if cat is not None and cat not in ALLOWED_CATEGORIES:
            issues.append(f"{rel}: category '{cat}' не в списке {sorted(ALLOWED_CATEGORIES)}")
        status = fm.get("status")
        if status is not None and status not in ALLOWED_STATUS:
            issues.append(f"{rel}: status '{status}' не в списке {sorted(ALLOWED_STATUS)}")
        tags = fm.get("tags")
        if not isinstance(tags, list) or not tags or not all(isinstance(t, str) for t in tags):
            issues.append(f"{rel}: tags должен быть непустым списком строк")
        updated = fm.get("updated")
        if updated is not None and not (
            isinstance(updated, str) and DATE_RE.match(updated)
            or isinstance(updated, _dt.date)
        ):
            issues.append(f"{rel}: updated должен быть датой YYYY-MM-DD")
        mv = fm.get("min_version")
        if mv is not None and not isinstance(mv, (str, int, float)):
            issues.append(f"{rel}: min_version должен быть строкой/числом или null")
    return issues


def manifest_entries() -> list[tuple[Path, dict]]:
    """Все записи manifest: (path к секции, entry dict).

    Ходит по всему дереву (languages, architecture, database, messaging, cicd, ...).
    """
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
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

    for key, value in data.items():
        if key in ("version", "updated"):
            continue
        walk(value, Path(str(key)))
    return entries


def check_manifest() -> list[str]:
    issues: list[str] = []
    if not MANIFEST.exists():
        return ["index/manifest.yaml: файл не найден"]
    try:
        data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [f"index/manifest.yaml: невалидный YAML: {e}"]
    if not isinstance(data, dict):
        return ["index/manifest.yaml: корневой объект должен быть mapping"]

    entries = manifest_entries()
    manifest_paths: set[str] = set()
    for section, entry in entries:
        rel = str(entry.get("path", ""))
        manifest_paths.add(rel)
        target = ROOT / rel
        if not target.exists():
            issues.append(f"manifest ({section}): путь '{rel}' не существует")
            continue
        try:
            fm = parse_frontmatter(target)
        except yaml.YAMLError:
            issues.append(f"manifest ({section}): '{rel}': невалидный YAML в frontmatter")
            continue
        if fm is None:
            issues.append(f"manifest ({section}): '{rel}' без frontmatter")
            continue
        for field in ("id", "title", "status"):
            if entry.get(field) != fm.get(field):
                issues.append(
                    f"manifest ({section}): '{rel}': {field}={entry.get(field)!r} "
                    f"!= frontmatter {fm.get(field)!r}"
                )

    # Обратное направление: все контент-файлы с frontmatter — в manifest.
    for path in all_md_files():
        rel = str(path.relative_to(ROOT))
        if path.name == "README.md" or rel.startswith("docs/"):
            continue
        try:
            fm = parse_frontmatter(path)
        except yaml.YAMLError:
            continue  # уже отмечено в check_frontmatter
        if fm is None:
            continue  # отсутствие frontmatter уже отмечено в check_frontmatter
        if rel not in manifest_paths:
            issues.append(f"manifest: файл '{rel}' с frontmatter отсутствует в каталоге")
    return issues


def check_links() -> list[str]:
    issues: list[str] = []
    for path in all_md_files():
        text = path.read_text(encoding="utf-8")
        # Убираем code blocks, чтобы не проверять ссылки в примерах кода.
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for match in LINK_RE.finditer(text):
            target = match.group(1)
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean = target.split("#", 1)[0].split("?", 1)[0]
            if not clean:
                continue
            resolved = (path.parent / clean).resolve()
            if not resolved.exists():
                issues.append(f"{path.relative_to(ROOT)}: битая ссылка -> {target}")
    return issues


CHECKS = {
    "frontmatter": check_frontmatter,
    "manifest": check_manifest,
    "links": check_links,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        choices=[*CHECKS, "all"],
        default="all",
        help="какую проверку запустить (по умолчанию: all)",
    )
    args = parser.parse_args()

    total = 0
    for name, fn in CHECKS.items():
        if args.check not in ("all", name):
            continue
        issues = fn()
        if issues:
            print(f"[{name}] {len(issues)} проблем(ы):")
            for issue in issues:
                print(f"  - {issue}")
            total += len(issues)
        else:
            print(f"[{name}] ok")
    if total:
        print(f"\nИТОГО: {total} проблем(ы)")
        return 1
    print("\nИТОГО: все проверки пройдены")
    return 0


if __name__ == "__main__":
    sys.exit(main())
