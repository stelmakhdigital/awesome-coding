#!/usr/bin/env python3
"""Отформатировать go-блоки записей gofmt'ом на месте.

Назначение: вердикт `fmt` роняет CI так же, как `fail` — код из записи копируют
как есть, и «почти gofmt» это всё ещё неправда. Править табы руками дорого,
поэтому блоки прогоняются через тот же gofmt, что и проверка: вырезали из
markdown, отформатировали в контейнере, вставили обратно.

Использование:
  python3 tools/gofmt_records.py go/snippets/websocket.md …
  python3 tools/gofmt_records.py --all          # все записи с go-блоками

Нужен docker (образ golang:1.27-alpine). Блоки собираются в один модуль ровно
так же, как их собирает verify_snippets: соседи видны, форматирование — то же.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import tempfile

try:
    import yaml  # noqa: F401  — нужен tools/ac.py
except ImportError:
    print("ОШИБКА: нужен PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

from ac import ROOT, content_files, fence_blocks  # noqa: E402
from verify_snippets import go_module_files  # noqa: E402

GO_IMAGE = "golang:1.27-alpine"


def fix_record(path: pathlib.Path) -> int:
    """Отформатировать go-блоки одной записи. Возвращает число изменённых блоков."""
    text = path.read_text(encoding="utf-8")
    blocks = [(i, code) for i, (_, code) in enumerate(fence_blocks(text, {"go"}), 1)]
    if not blocks:
        return 0

    workdir = pathlib.Path(tempfile.mkdtemp())
    files = go_module_files(blocks)
    for name, body in files.items():
        target = workdir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")

    subprocess.run(
        ["docker", "run", "--rm", "-v", f"{workdir}:/w", "-w", "/w", GO_IMAGE, "sh", "-c", "gofmt -w ."],
        check=True,
    )

    by_index = dict(blocks)
    changed = 0
    for name in files:
        fname = name.name if isinstance(name, pathlib.PurePosixPath) else str(name).rsplit("/", 1)[-1]
        if not fname.startswith("block"):
            continue
        idx = int(fname[len("block"):-len(".go")])
        original = by_index[idx]
        formatted = (workdir / name).read_text(encoding="utf-8").rstrip("\n")
        if formatted == original.rstrip("\n"):
            continue
        if original not in text:
            print(f"  ПРОПУСК {path}: блок #{idx} не найден в тексте дословно", file=sys.stderr)
            continue
        text = text.replace(original, formatted, 1)
        changed += 1

    if changed:
        path.write_text(text, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("Назначение")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("records", nargs="*", help="пути к записям (относительно корня репозитория)")
    parser.add_argument("--all", action="store_true", help="все записи с go-блоками")
    args = parser.parse_args()

    if not args.records and not args.all:
        parser.print_help()
        return 2

    paths = [ROOT / r for r in args.records]
    if args.all:
        paths = list(content_files())

    total = 0
    for path in paths:
        changed = fix_record(path)
        if changed:
            rel = path.relative_to(ROOT) if path.is_absolute() else path
            print(f"{rel}: переформатировано блоков {changed}")
        total += changed

    print(f"изменено блоков: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
