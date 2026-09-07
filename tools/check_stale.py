#!/usr/bin/env python3
"""Пересмотр устаревших записей: frontmatter `updated` старше порога.

Порог по умолчанию — 180 дней (квартальный аудит × 2). Запуск:
  make check-stale            # 180 дней
  python3 tools/check_stale.py --days 90

Вывод: записи старше порога (самые старые первыми). Exit code: 0 — всегда
(информационный отчёт); при находках — обновите контент и дату `updated`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ОШИБКА: нужен PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules"}


def content_files() -> list[Path]:
    return sorted(
        p for p in ROOT.rglob("*.md")
        if not (SKIP_DIRS & set(p.parts))
        and p.name != "README.md"
        and not any(part == "docs" for part in p.parts)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=180, help="порог устаревания (дни)")
    args = parser.parse_args()

    today = dt.date.today()
    stale: list[tuple[dt.date, str]] = []
    missing: list[str] = []
    for path in content_files():
        rel = str(path.relative_to(ROOT))
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        end = text.find("\n---\n", 4)
        if end == -1:
            continue
        try:
            fm = yaml.safe_load(text[4:end])
        except yaml.YAMLError:
            continue
        if not isinstance(fm, dict):
            continue
        updated = fm.get("updated")
        if isinstance(updated, dt.date):
            if (today - updated).days > args.days:
                stale.append((updated, rel))
        else:
            missing.append(rel)

    if stale:
        print(f"Записей старше {args.days} дней: {len(stale)} (пересмотрите и обновите `updated`):")
        for date, rel in sorted(stale):
            print(f"  - {date}  {rel}")
    else:
        print(f"Все записи свежее {args.days} дней.")
    if missing:
        print(f"\nНет/не распознано поле `updated`: {len(missing)}")
        for rel in missing:
            print(f"  - {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
