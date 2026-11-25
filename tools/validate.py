#!/usr/bin/env python3
"""Валидатор awesome-coding: frontmatter, manifest, ссылки.

Проверки:
  frontmatter — YAML frontmatter всех .md: обязательные поля, допустимые
                значения, уникальные id, формат полей.
  manifest    — index/*.yaml (шапка + секции): пути существуют, все
                контент-файлы есть в каталоге, id/title/status/tags/updated
                совпадает с frontmatter, verified честен для сниппетов с
                кодом, sections ↔ файлы index/*.yaml.
  indexes     — README каталога упоминает все .md каталога (блок «Статус
                разделов» основного README генерируется: tools/readme.py).
  structure   — у snippet/pattern есть «Когда использовать», «Когда НЕ
                использовать» и Related.
  text        — в тексте нет CJK-символов и смешения раскладок («batч», «Кrash»).
  aliases     — index/aliases.yaml: форма ключей, несуществующие id.
  links       — относительные markdown-ссылки указывают на существующие файлы.

Использование:
  python3 tools/validate.py [--check frontmatter|manifest|indexes|text|links|all]

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

from ac import (  # noqa: E402  — разбор формата один на весь тулинг (tools/ac.py)
    INDEX_DIR,
    MANIFEST,
    NO_FRONTMATTER,
    NO_FRONTMATTER_DIRS,
    ROOT,
    all_md_files,
    code_fences,
    content_files,
    index_entries,
    index_files,
    needs_frontmatter,
    parse_frontmatter,
)

# Допустимые имена секционных файлов index/<section>.yaml.
ALLOWED_SECTIONS = {
    "go", "typescript", "javascript", "react", "python", "c", "bash",
    "csharp", "kotlin", "unity", "agenting", "shared", "architecture",
    "database", "messaging", "cicd", "pm", "llm",
}

ALLOWED_LANGS = {
    "go", "typescript", "javascript", "react", "python", "c", "bash",
    "csharp", "kotlin", "unity", "agenting", "shared", "architecture",
    "database", "messaging", "cicd", "pm", "llm",
}
ALLOWED_CATEGORIES = {"concept", "rule-set", "idioms", "decisions", "snippet", "pattern"}
ALLOWED_STATUS = {"stable", "experimental", "deprecated"}
ALLOWED_VERIFIED = {"compiled", "executed", "reviewed", "none"}
SKILL_FIELDS = ("name", "description", "whenToUse", "updated")
ID_PREFIXES = (
    "go", "ts", "js", "react", "py", "c", "bash", "csharp", "kotlin", "unity", "agenting",
    "shared", "ddd", "arch", "database", "messaging", "cicd", "pm", "llm",
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
        if not needs_frontmatter(path):
            continue  # свой формат frontmatter (skills/)
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
        elif (iso := norm_date(updated)) and iso > _dt.date.today().isoformat():
            # Дата ставится по коммиту, который трогает запись. Три релиза были
            # подписаны завтрашним числом: дату пишут руки, проверить нечему, и
            # «свежесть» записи превращается в догадку.
            issues.append(f"{rel}: updated={iso} в будущем (сегодня {_dt.date.today().isoformat()})")
        mv = fm.get("min_version")
        if mv is not None and not isinstance(mv, (str, int, float)):
            issues.append(f"{rel}: min_version должен быть строкой/числом или null")

    # Скиллы живут по своему формату frontmatter — проверяем минимум.
    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        rel = skill.relative_to(ROOT)
        try:
            fm = parse_frontmatter(skill) or {}
        except yaml.YAMLError:
            issues.append(f"{rel}: невалидный YAML в frontmatter")
            continue
        for field in SKILL_FIELDS:
            if not fm.get(field):
                issues.append(f"{rel}: нет поля '{field}' (формат скилла)")
    return issues


def manifest_files() -> list[Path]:
    """Каталог: index/manifest.yaml (шапка) + index/<section>.yaml (записи)."""
    return index_files()


def manifest_entries() -> list[tuple[Path, dict]]:
    """Все записи каталога: (section, entry dict). Секция = `<section>/<ключ>`."""
    return index_entries()


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
        if sorted(str(t) for t in entry.get("tags") or []) != sorted(
            str(t) for t in fm.get("tags") or []
        ):
            issues.append(
                f"manifest ({section}): '{rel}': tags={entry.get('tags')!r} "
                f"!= frontmatter {fm.get('tags')!r}"
            )
        # verified=none означает «кода нет» — для сниппетов/паттернов с кодом
        # это обещание, а не факт.
        if verified == "none" and fm.get("category") in ("snippet", "pattern"):
            found = code_fences(target.read_text(encoding="utf-8"))
            if found:
                issues.append(
                    f"manifest ({section}): '{rel}': verified=none, но в записи "
                    f"есть код на {sorted(found)} — поднимите verified до "
                    f"compiled/executed/reviewed"
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
        if path.name in NO_FRONTMATTER or any(p in NO_FRONTMATTER_DIRS for p in path.parts):
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
    """README каталога упоминает все .md этого каталога.

    Блок «Статус разделов» основного README не проверяется здесь: он генерируется
    из каталога (`tools/readme.py --check`)."""
    issues: list[str] = []
    # README каталога → каждый .md каталога упомянут по basename.
    for readme in sorted(ROOT.rglob("README.md")):
        if "node_modules" in readme.parts or readme.parent == ROOT:
            continue
        text = readme.read_text(encoding="utf-8")
        for f in sorted(readme.parent.glob("*.md")):
            if f.name != "README.md" and f.name not in text:
                issues.append(f"{readme.relative_to(ROOT)}: не упомянут {f.name}")

    return issues


REQUIRE_BY_CATEGORY = {
    "snippet": ("Когда использовать", "Когда НЕ использовать", "Related"),
    "pattern": ("Когда использовать", "Related"),
}


def check_structure() -> list[str]:
    """Содержание записи соответствует category.

    «Когда использовать / Когда НЕ использовать» — то, по чему агент решает,
    брать ли сниппет; Related — чтобы не выдумывал связи сам. Правило дешёвое,
    а без него через десяток записей остаются только примеры кода.
    """
    issues: list[str] = []
    for path in content_files():
        text = path.read_text(encoding="utf-8")
        m = re.search(r"^category: (\w[\w-]*)", text, re.M)
        if not m or m.group(1) not in REQUIRE_BY_CATEGORY:
            continue
        rel = path.relative_to(ROOT).as_posix()
        for heading in REQUIRE_BY_CATEGORY[m.group(1)]:
            if heading not in text:
                issues.append(f"{rel}: category={m.group(1)} — нет раздела «{heading}»")
    return issues


# Ключ алиаса — слово, которым ищут, а не тег: русские запросы к латинскому
# словарю тегов живут здесь, поэтому кириллица разрешена (теги остаются
# латиницей). Форма та же: строчные, дефисы, без пробелов и подчёркиваний.
ALIAS_FORM = re.compile(r"^[a-zа-яё0-9][a-zа-яё0-9.-]*$")


def check_aliases() -> list[str]:
    """index/aliases.yaml: ключ в форме тега, все target-ы — существующие записи.

    Алиасы — единственное место каталога, где связь «слово → запись» держится
    руками. Без проверки опечатка в id или переезд записи молча превращают
    подсказку поиска в несбыточное обещание.
    """
    path = INDEX_DIR / "aliases.yaml"
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return [f"index/aliases.yaml: невалидный YAML — {e}"]
    aliases = data.get("aliases")
    if not isinstance(aliases, dict):
        return ["index/aliases.yaml: нужен ключ `aliases:` со словарём"]

    entries = [e for _, e in index_entries()]
    ids = {str(e.get("id")) for e in entries}
    tags = {str(t).lower() for e in entries for t in (e.get("tags") or [])}

    issues: list[str] = []
    for key, targets in aliases.items():
        k = str(key)
        if not ALIAS_FORM.match(k):
            issues.append(f"index/aliases.yaml: ключ «{k}» не в форме тега "
                          "(строчные буквы, дефисы, без пробелов)")
        elif k in tags or k in ids:
            issues.append(f"index/aliases.yaml: «{k}» — уже тег или id; "
                          "допишите тег записи, алиас не нужен")
        if not isinstance(targets, list) or not targets:
            issues.append(f"index/aliases.yaml: «{k}» — нужен непустой список id")
            continue
        for target in targets:
            if str(target) not in ids:
                issues.append(f"index/aliases.yaml: «{k}» → {target}: записи нет в каталоге")
    return issues


def check_text() -> list[str]:
    """Текст: без CJK и без прилипшей латиницы к кириллице.

    Контент пишут агенты: во фразу попадают иероглифы и слова, набранные в латинской
    раскладке («batч», «Кrash»). Разделитель (пробел, дефис) — норма, слитное
    написание — опечатка раскладки; латинские части составных слов склеены дефисом.
    """
    cjk = re.compile(r"[\u3000-\u9fff\uff00-\uffef]")
    sticky = re.compile(r"[а-яА-Я][A-Za-z]{3,}|[A-Za-z]{3,}[а-яА-Я]")
    fence = re.compile(r"^```.*?^```", re.M | re.S)
    inline = re.compile(r"`[^`\n]*`")
    issues: list[str] = []
    for path in sorted(ROOT.rglob("*.md")):
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        rel = path.relative_to(ROOT).as_posix()
        # Код вырезается с сохранением нумерации строк: номера в отчёте
        # должны совпадать с файлом.
        text = fence.sub(lambda m: "\n" * m.group(0).count("\n"),
                         path.read_text(encoding="utf-8"))
        for i, line in enumerate(text.splitlines(), 1):
            line = inline.sub("", line)  # inline-код — цитата кода, не проза
            if cjk.search(line):
                issues.append(f"{rel}:{i}: CJK-символы — «{line.strip()[:60]}»")
            elif sticky.search(line):
                issues.append(f"{rel}:{i}: смешение раскладок — «{line.strip()[:60]}»")
    return issues


LEVEL_RANK = {"none": 0, "reviewed": 1, "compiled": 2, "executed": 3}


def check_verified_claims() -> list[str]:
    """`verified` не может быть выше того, что способно доказать о записи.

    Раннер языка доказывает `compiled` (блоки прошли тулчейн), а `executed` —
    только там, где он блок выполняет, а не собирает (SQL). Язык без раннера в
    CI не проверяется вовсе. Всё остальное требует поля `proof:` в frontmatter:
    чем, где и когда это запускали (ADR-0006).

    Язык «покрыт» только если раннер берёт блоки этой записи в прогон: отбор
    берётся из `collect()`, а не повторяется здесь. Со своей реализацией проверка
    разошлась бы с раннером — так она пропускала unity-блоки, которые csharp-
    раннер отбрасывает намеренно, и разрешала `compiled` там, где CI ничего не
    собирает (issue #7).

    Чего проверка не видит: вердикты прогона. Запись, все блоки которой дают
    `deps` или `fragment`, статически выглядит доказуемой; уровень у неё поднимет
    только `make verify-fix`, а не эта проверка.
    """
    from verify_snippets import CONFIG_LANGS, RUNNERS, collect  # поздний импорт

    exec_proven = {lang for lang, r in RUNNERS.items() if r.executes}
    levels = {str(e.get("path")): str(e.get("verified")) for _, e in index_entries()}
    taken: dict[str, set[str]] = {}
    for job in collect(sorted(RUNNERS), None, None):
        taken.setdefault(job.path, set()).add(job.lang)

    issues: list[str] = []
    for path in content_files():
        rel = path.relative_to(ROOT).as_posix()
        level = levels.get(rel, "")
        if LEVEL_RANK.get(level, 0) <= LEVEL_RANK["reviewed"]:
            continue
        langs = code_fences(path.read_text(encoding="utf-8")) - CONFIG_LANGS
        covered = taken.get(rel, set())
        uncovered = langs - covered
        proven = bool(covered) and not uncovered
        if level == "executed":
            # Достаточно, чтобы хотя бы один язык записи выполнялся в CI: в
            # смешанных записях (SQL + Go) предмет записи — запрос, и он
            # прогоняется; собранные блоки ниже этого уровня и не тянут.
            proven = proven and bool(covered & exec_proven)
        if proven:
            continue
        fm = parse_frontmatter(path) or {}
        if str(fm.get("proof", "")).strip():
            continue
        all_langs = ", ".join(sorted(langs)) or "нет кода"
        not_covered = ", ".join(sorted(uncovered))
        only_lint = ", ".join(sorted(covered))
        if not covered:
            why = "нет блоков, которые CI умеет прогонять (" + all_langs + ")"
        elif level == "executed":
            why = "раннеры " + only_lint + " блоки не выполняют"
        else:
            why = "нет раннера для " + not_covered
        issues.append(
            f"{rel}: verified={level} не доказан CI ({why}), нужно поле `proof:` "
            "в frontmatter — чем, где и когда это запускали")
    return issues


CHECKS = {
    "frontmatter": check_frontmatter,
    "manifest": check_manifest,
    "indexes": check_indexes,
    "verified": check_verified_claims,
    "structure": check_structure,
    "text": check_text,
    "aliases": check_aliases,
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
