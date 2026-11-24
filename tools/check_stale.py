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

try:
    import yaml  # noqa: F401  — нужен tools/ac.py
except ImportError:
    print("ОШИБКА: нужен PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

from ac import ROOT, all_md_files, parse_frontmatter  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=180, help="порог устаревания (дни)")
    args = parser.parse_args()

    today = dt.date.today()
    stale: list[tuple[dt.date, str]] = []
    missing: list[str] = []
    for path in all_md_files():
        try:
            fm = parse_frontmatter(path)
        except yaml.YAMLError:
            continue  # невалидный YAML отмечает validate.py
        if not isinstance(fm, dict):
            continue
        rel = str(path.relative_to(ROOT))
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
