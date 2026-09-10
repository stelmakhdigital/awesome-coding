#!/usr/bin/env python3
"""Валидатор awesome-coding: frontmatter, manifest, ссылки.

Проверки:
  frontmatter — YAML frontmatter всех .md: обязательные поля, допустимые
                значения, уникальные id, формат полей.
  manifest    — index/*.yaml (шапка + секции): пути существуют, все
                контент-файлы есть в каталоге, id/title/status/updated
                совпадает с frontmatter, sections ↔ файлы index/*.yaml.
  indexes     — README каталога упоминает все .md каталога; счётчики
                «Статус разделов» в основном README совпадают с фактом.
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
INDEX_DIR = ROOT / "index"
MANIFEST = INDEX_DIR / "manifest.yaml"

# Допустимые имена секционных файлов index/<section>.yaml.
ALLOWED_SECTIONS = {
    "go", "typescript", "javascript", "python", "c", "bash",
    "csharp", "kotlin", "unity", "shared", "architecture",
    "database", "messaging", "cicd", "pm",
}

# Файлы, которым frontmatter НЕ требуется.
NO_FRONTMATTER = {
    "README.md",  # любой README (индексы разделов)
    "AGENTS.md",
}
NO_FRONTMATTER_DIRS = {"docs"}

ALLOWED_LANGS = {
    "go", "typescript", "javascript", "python", "c", "bash",
    "csharp", "kotlin", "unity", "shared", "database", "messaging", "cicd", "pm",
}
ALLOWED_CATEGORIES = {"concept", "rule-set", "idioms", "decisions", "snippet", "pattern"}
ALLOWED_STATUS = {"stable", "experimental", "deprecated"}
ALLOWED_VERIFIED = {"compiled", "executed", "reviewed", "none"}
ID_PREFIXES = (
    "go", "ts", "js", "py", "c", "bash", "csharp", "kotlin", "unity",
    "shared", "ddd", "arch", "database", "messaging", "cicd", "pm",
)
REQUIRED_FIELDS = ("id", "title", "lang", "min_version", "category", "tags", "status", "updated")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def norm_date(v) -> str | None:
    """Дата из YAML (datetime.date) или строка → ISO-строка."""
    if v is None:
        return None
    return v.isoformat() if hasattr(v, "isoformat") else str(v)
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
    skip = {".git", "node_modules"}
    return sorted(p for p in ROOT.rglob("*.md") if not (skip & set(p.parts)))


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


def manifest_files() -> list[Path]:
    """Каталог: index/manifest.yaml (шапка) + index/<section>.yaml (записи)."""
    return sorted(INDEX_DIR.glob("*.yaml"))


def manifest_entries() -> list[tuple[Path, dict]]:
    """Все записи каталога: (section, entry dict).

    Ходит по всем файлам index/*.yaml; секция = имя файла без расширения.
    """
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

    for mf in manifest_files():
        try:
            data = yaml.safe_load(mf.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue  # невалидный YAML уже отмечен в check_manifest
        if not isinstance(data, dict):
            continue
        for key, value in data.items():
            if key in ("version", "updated", "languages"):
                continue
            walk(value, Path(mf.stem) / str(key))
    return entries


def check_manifest() -> list[str]:
    issues: list[str] = []
    files = manifest_files()
    if not files:
        return ["index/: файлы каталога не найдены"]
    if not MANIFEST.exists():
        issues.append("index/manifest.yaml: шапка каталога не найдена")
    for mf in files:
        rel = f"index/{mf.name}"
        try:
            data = yaml.safe_load(mf.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            issues.append(f"{rel}: невалидный YAML: {str(e).splitlines()[0]}")
            continue
        if not isinstance(data, dict):
            issues.append(f"{rel}: корневой объект должен быть mapping")
        elif mf.name != "manifest.yaml" and mf.stem not in ALLOWED_SECTIONS:
            issues.append(
                f"{rel}: имя файла должно быть названием раздела "
                f"{sorted(ALLOWED_SECTIONS)}"
            )
    if MANIFEST.exists():
        try:
            head = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
            if isinstance(head, dict):
                if "updated" not in head:
                    issues.append("index/manifest.yaml: нет поля 'updated'")
                if "sections" not in head:
                    issues.append("index/manifest.yaml: нет поля 'sections' (список разделов)")
                else:
                    listed = {str(s) for s in head.get("sections") or []}
                    on_disk = {mf.stem for mf in files if mf.name != "manifest.yaml"}
                    for s in sorted(listed - on_disk):
                        issues.append(
                            f"index/manifest.yaml: раздел '{s}' в sections, "
                            f"но index/{s}.yaml не существует"
                        )
                    for s in sorted(on_disk - listed):
                        issues.append(
                            f"index/manifest.yaml: index/{s}.yaml существует, "
                            f"но '{s}' отсутствует в sections"
                        )
        except yaml.YAMLError:
            pass  # уже отмечено выше

    entries = manifest_entries()
    manifest_paths: set[str] = set()
    for section, entry in entries:
        rel = str(entry.get("path", ""))
        manifest_paths.add(rel)
        verified = entry.get("verified")
        if verified not in ALLOWED_VERIFIED:
            issues.append(
                f"manifest ({section}): '{rel}': verified={verified!r} "
                f"не в списке {sorted(ALLOWED_VERIFIED)}"
            )
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
        idx_upd = entry.get("updated")
        if idx_upd is None:
            issues.append(f"manifest ({section}): '{rel}': нет поля 'updated'")
        elif norm_date(idx_upd) != norm_date(fm.get("updated")):
            issues.append(
                f"manifest ({section}): '{rel}': updated={idx_upd!r} "
                f"!= frontmatter {fm.get('updated')!r}"
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


def check_indexes() -> list[str]:
    """Синхронизация индексов: README каталога упоминает все .md каталога,
    счётчики в основном README совпадают с фактическим числом файлов."""
    issues: list[str] = []
    # 1) README каталога → каждый .md каталога упомянут по basename.
    for readme in sorted(ROOT.rglob("README.md")):
        if "node_modules" in readme.parts or readme.parent == ROOT:
            continue
        text = readme.read_text(encoding="utf-8")
        for f in sorted(readme.parent.glob("*.md")):
            if f.name != "README.md" and f.name not in text:
                issues.append(f"{readme.relative_to(ROOT)}: не упомянут {f.name}")

    # 2) Счётчики в «Статус разделов» основного README.
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "## Статус разделов" not in readme:
        return issues
    status = readme.split("## Статус разделов", 1)[1].split("\n## ", 1)[0]

    def count_files(p: Path) -> int | None:
        if not p.exists():
            return None
        return len([f for f in p.glob("*.md") if f.name != "README.md"])

    for line in status.splitlines():
        m = re.match(r"^\|\s*`([a-z-]+)/`\s*\|(.+)\|$", line)
        if not m:
            continue
        section, desc = m.group(1), m.group(2)
        n = re.search(r"(\d+)\s+сниппет", desc)
        if n:
            actual = count_files(ROOT / section / "snippets")
            if actual is not None and int(n.group(1)) != actual:
                issues.append(
                    f"README: {section}/ — указано {n.group(1)} сниппетов, фактически {actual}"
                )
        n = re.search(r"(\d+)\s+кросс-языковых концепций", desc)
        if n:
            actual = count_files(ROOT / "shared")
            if actual is not None and int(n.group(1)) != actual:
                issues.append(
                    f"README: shared/ — указано {n.group(1)} концепций, фактически {actual}"
                )
        n = re.search(r"(\d+)\s+архитектурных паттернов", desc)
        if n:
            actual = count_files(ROOT / "architecture" / "patterns")
            if actual is not None and int(n.group(1)) != actual:
                issues.append(
                    f"README: architecture/ — указано {n.group(1)} паттернов, фактически {actual}"
                )
    return issues


CHECKS = {
    "frontmatter": check_frontmatter,
    "manifest": check_manifest,
    "indexes": check_indexes,
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
