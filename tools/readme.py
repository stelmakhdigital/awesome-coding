#!/usr/bin/env python3
"""Генерация блока «Статус разделов» в README из каталога index/*.yaml.

Счётчики и версии в README раньше были ручными и расходились с фактом (плюс
устаревающие обещания вроде «ASan-чисто»). Теперь таблица генерируется:

  python3 tools/readme.py            — перезаписать блок
  python3 tools/readme.py --check    — проверить, что блок совпадает (для CI)

Блок ищется между заголовком `## Статус разделов` и следующим `##`; правки
текста внутри него бессмысленны — меняйте каталог.
"""

from __future__ import annotations

import argparse
import re
import sys

try:
    import yaml
except ImportError:
    print("ОШИБКА: нужен PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

from ac import INDEX_DIR, MANIFEST, ROOT, code_fences, index_entries  # noqa: E402

CHECKED = {"compiled", "executed"}
TITLE = "## Статус разделов"
CATEGORY_NAMES = {
    "snippet": ("сниппет", "сниппета", "сниппетов"),
    "pattern": ("паттерн", "паттерна", "паттернов"),
    "rule-set": ("набор правил", "набора правил", "наборов правил"),
    "idioms": ("idioms", "idioms", "idioms"),
    "decisions": ("таблица решений", "таблицы решений", "таблиц решений"),
    "concept": ("концепция", "концепции", "концепций"),
}


def count_form(n: int, cat: str) -> str:
    """«1 сниппет / 2 сниппета / 5 сниппетов»."""
    forms = CATEGORY_NAMES.get(cat) or (cat, cat, cat)
    if 11 <= n % 100 <= 14:
        return f"{n} {forms[2]}"
    return f"{n} {forms[{1: 0, 2: 1, 3: 1, 4: 1}.get(n % 10, 2)]}"
# Разделы, где код проверяется вне make verify (нужны живые PG/SDK/Editor).
OUT_OF_CI = {"database": "SQL — живой PostgreSQL 18", "csharp": "dotnet build",
             "kotlin": "kotlinc", "unity": "Unity Editor"}


def sections() -> list[str]:
    head = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return list(head.get("sections") or [])


def section_stats(section: str) -> tuple[str, dict[str, int], int, int]:
    """(версия, счётчики по категориям, записей с кодом, из них проверено)."""
    index = INDEX_DIR / f"{section}.yaml"
    version = "—"
    if index.exists():
        version = str(yaml.safe_load(index.read_text(encoding="utf-8")).get("version") or "—")
    cats: dict[str, int] = {}
    with_code = checked = 0
    for _, entry in index_entries():
        if not entry.get("path", "").startswith(section + "/"):
            continue
        path = ROOT / entry["path"]
        text = path.read_text(encoding="utf-8")
        cat = re.search(r"^category: (\S+)", text, re.M)
        key = cat.group(1) if cat else "?"
        cats[key] = cats.get(key, 0) + 1
        if code_fences(text):
            with_code += 1
            if entry.get("verified") in CHECKED:
                checked += 1
    return version, cats, with_code, checked


def table() -> str:
    lines = [
        "| Раздел | Версия | Записей | Состав | Код проверен | Guardrails |",
        "|---|---|---|---|---|---|",
    ]
    total = total_code = total_checked = 0
    for section in sections():
        version, cats, with_code, checked = section_stats(section)
        total += sum(cats.values())
        total_code += with_code
        total_checked += checked
        makeup = ", ".join(count_form(n, cat) for cat, n in
                           sorted(cats.items(), key=lambda x: -x[1]))
        guard = "rules.md" if (ROOT / section / "rules.md").exists() else "—"
        code = f"{checked}/{with_code}" if with_code else "—"
        lines.append(f"| `{section}/` | {version} | {sum(cats.values())} | {makeup} "
                     f"| {code} | {guard} |")
    lines.append(f"| **итого** | | **{total}** | | **{total_checked}/{total_code}** | |")
    return "\n".join(lines)


def render() -> str:
    notes = "; ".join(f"`{s}` — {why}" for s, why in OUT_OF_CI.items())
    return (
        "Счётчики и версии генерируются из `index/*.yaml` (`make readme`), вручную не правятся.\n"
        "«Код проверен» — записи с программным кодом, прошедшие прогон тулчейном\n"
        f"(`compiled`/`executed`, см. [docs/FORMAT.md](docs/FORMAT.md)). Вне `make verify` остаются\n"
        f"{notes} — там уровень ставится по фактической проверке.\n\n" + table() + "\n"
    )


def replace_block(text: str, body: str) -> str:
    start = text.index(TITLE)
    end = text.find("\n## ", start + len(TITLE))
    end = len(text) if end == -1 else end
    return text[:start] + TITLE + "\n\n" + body + ("\n" + text[end + 1:] if end < len(text) else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="не писать, а сверить")
    args = parser.parse_args()

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    if TITLE not in text:
        print(f"README.md: нет блока «{TITLE}»", file=sys.stderr)
        return 2
    body = render()
    current = text[text.index(TITLE) + len(TITLE):]
    current = current[: current.find("\n## ")] if "\n## " in current else current
    if args.check:
        if current.strip() != ("\n" + body).strip():
            print("README: блок «Статус разделов» устарел — запустите make readme",
                  file=sys.stderr)
            return 1
        print("[readme] ok\n\nИТОГО: все проверки пройдены")
        return 0
    readme.write_text(replace_block(text, body), encoding="utf-8")
    print("README: блок «Статус разделов» перегенерирован")
    return 0


if __name__ == "__main__":
    sys.exit(main())
