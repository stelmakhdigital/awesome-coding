#!/usr/bin/env python3
"""Подготовка релиза: блок в CHANGELOG и пин версии в SKILL.md.

Шаги релиза раньше выполнялись руками через `str.replace`, и несовпавший якорь
не вставлял блок CHANGELOG молча — три релиза вышли с поднятым пином и без
записи. Здесь те же правки, но с жёсткими проверками: неверный якорь, версия или
отсутствующий пин — это падение, а не тихий пропуск.

Использование:
  python3 tools/release.py prepare --version v1.12 --date 2026-11-25 --body entry.md
  python3 tools/release.py check --version v1.12
"""

from __future__ import annotations

import argparse
import re
import sys

from ac import ROOT

CHANGELOG = ROOT / "CHANGELOG.md"
SKILL = ROOT / "skills" / "awesome-coding" / "SKILL.md"

VERSION_RE = re.compile(r"^v\d+\.\d+(\.\d+)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PIN_RE = re.compile(r"^ac=(v[\d.]+)\s*(#.*)?$", re.M)
HEADING_RE = re.compile(r"^## v", re.M)


def insert_entry(changelog: str, version: str, date: str, body: str) -> str:
    """Вставить блок `## version — date` перед первым существующим блоком версии."""
    if not VERSION_RE.match(version):
        raise ValueError(f"версия должна быть вида v1.2 или v1.2.3: {version!r}")
    if not DATE_RE.match(date):
        raise ValueError(f"дата в формате YYYY-MM-DD: {date!r}")
    if re.search(rf"^## {re.escape(version)}(?:\s|—|$)", changelog, re.M):
        raise ValueError(f"{version} уже есть в CHANGELOG")
    if not body.strip():
        raise ValueError("тело записи пустое")

    heading = f"## {version} — {date}\n\n{body.strip()}\n"

    first = HEADING_RE.search(changelog)
    if first is None:
        raise ValueError("в CHANGELOG нет ни одного блока версии — формат сломан")
    pos = first.start()
    return changelog[:pos] + heading + "\n" + changelog[pos:]


def version_tuple(v: str) -> tuple:
    return tuple(int(x) for x in v.lstrip("v").split("."))


def bump_pin(skill: str, version: str, allow_downgrade: bool = False) -> str:
    """Поднять пин `ac=vN.N` в SKILL.md. Отсутствие строки — ошибка, а не «нечего делать»."""
    if not VERSION_RE.match(version):
        raise ValueError(f"некорректная версия: {version!r}")
    pin = PIN_RE.search(skill)
    if pin is None:
        raise ValueError("в SKILL.md нет строки пина вида `ac=v1.2`")

    # Опустить пин — значит сказать агентам, что кэш протух в обратную сторону.
    # Обычно это опечатка в версии, а не намерение.
    if not allow_downgrade and version_tuple(pin.group(1)) > version_tuple(version):
        raise ValueError(
            f"пин опускается: {pin.group(1)} → {version}. Если это намеренно, передайте allow_downgrade")

    def sub(m: re.Match) -> str:
        return f"ac={version}" + (f"  {m.group(2)}" if m.group(2) else "")

    return PIN_RE.sub(sub, skill, count=1)


def check(changelog: str, skill: str, version: str) -> list[str]:
    """Список проблем; пустой список — к тегу готов."""
    problems: list[str] = []

    if not re.search(rf"^## {re.escape(version)}(?:\s|—|$)", changelog, re.M):
        problems.append(f"в CHANGELOG нет блока {version}")

    top = HEADING_RE.search(changelog)
    if top and not changelog[top.start():].startswith(f"## {version}"):
        problems.append(f"{version} не самый верхний блок CHANGELOG")

    pin = PIN_RE.search(skill)
    if pin is None:
        problems.append("в SKILL.md нет строки пина")
    elif pin.group(1) != version:
        problems.append(f"пин в SKILL.md = {pin.group(1)}, ожидался {version}")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("Шаги релиза")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    prep = sub.add_parser("prepare", help="вставить блок CHANGELOG и поднять пин")
    prep.add_argument("--version", required=True)
    prep.add_argument("--date", required=True)
    prep.add_argument("--body", required=True, help="файл с текстом записи")
    prep.add_argument("--allow-downgrade", action="store_true",
                      help="разрешить понижение пина (переиздание старой версии)")

    chk = sub.add_parser("check", help="проверить готовность к тегу")
    chk.add_argument("--version", required=True)

    args = parser.parse_args()
    changelog = CHANGELOG.read_text(encoding="utf-8")
    skill = SKILL.read_text(encoding="utf-8")

    if args.cmd == "check":
        problems = check(changelog, skill, args.version)
        for p in problems:
            print(f"ПРОБЛЕМА: {p}")
        if problems:
            return 1
        print(f"{args.version}: CHANGELOG и пин согласованы")
        return 0

    body = (ROOT / args.body).read_text(encoding="utf-8") if (ROOT / args.body).exists() else args.body
    new_changelog = insert_entry(changelog, args.version, args.date, body)
    new_skill = bump_pin(skill, args.version, allow_downgrade=args.allow_downgrade)

    CHANGELOG.write_text(new_changelog, encoding="utf-8")
    SKILL.write_text(new_skill, encoding="utf-8")

    old = PIN_RE.search(skill)
    print(f"CHANGELOG: добавлен блок {args.version} ({args.date})")
    print(f"SKILL.md: пин {old.group(1) if old else '—'} → {args.version}")

    problems = check(new_changelog, new_skill, args.version)
    for p in problems:
        print(f"ПРОБЛЕМА после правки: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
