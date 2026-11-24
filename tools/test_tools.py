#!/usr/bin/env python3
"""Тесты туллинга: `make test`. stdlib unittest, отдельных зависимостей нет.

Зачем: туллинг — то, чему доверяет репозиторий. `make validate` зелёный значит
«записи в порядке» только пока сам валидатор не сломался. Гонка в SQL-раннере
упала в CI через два релиза после появления, потому что проверить её было нечем.

Что покрыто: вердикты раннеров, разбор формата (frontmatter, блоки каталога),
текстовые и структурные проверки, каталог, алиасы, порядок поиска, русские
формы счётчика. Проверки, которым нужен живой тулчейн или сеть (verify,
check-versions, mermaid), здесь не запускаются.

Запуск: python3 tools/test_tools.py [-v]
"""

from __future__ import annotations

import contextlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ac
import find
import readme
import validate
import verify_snippets as vs

# Минимальный «репозиторий»: одна чистая запись go-x + чистый каталог.
CLEAN_FM = """---
id: go-x
title: Go X
lang: go
min_version: "1.27"
category: snippet
tags: [http, context, client]
status: stable
updated: 2026-01-01
---

# Go X

**Когда использовать** — кратко.
**Когда НЕ использовать** — кратко.

## Код

```go
package main
```

## Pitfalls
- Пусто.

## Related
- Нет.
"""

CLEAN_INDEX = """snippets:
  - id: go-x
    title: Go X
    path: go/snippets/x.md
    tags: [http, context, client]
    status: stable
    verified: compiled
    updated: 2026-01-01
"""

CLEAN_MANIFEST = """version: "test"
updated: 2026-01-01
languages: {}
sections: [go]
"""


@contextlib.contextmanager
def temp_repo(**files: str):
    """Временный каталог вместо репозитория: пути туллинга переключаются и возвращаются.

    Проверки берут пути из своих модулей (`validate.ROOT`, `ac.ROOT`, ...), поэтому
    патчим все: иначе часть проверок читает настоящий репозиторий и тест проходит
    «впустую».
    """
    tree = {
        "index/manifest.yaml": CLEAN_MANIFEST,
        "index/go.yaml": CLEAN_INDEX,
        "go/snippets/x.md": CLEAN_FM,
        **files,
    }
    saved = {
        (ac, "ROOT"): ac.ROOT, (ac, "INDEX_DIR"): ac.INDEX_DIR, (ac, "MANIFEST"): ac.MANIFEST,
        (validate, "ROOT"): validate.ROOT, (validate, "INDEX_DIR"): validate.INDEX_DIR,
        (validate, "MANIFEST"): validate.MANIFEST,
        (find, "ALIASES_FILE"): find.ALIASES_FILE,
    }
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for rel, text in tree.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        ac.ROOT = root
        ac.INDEX_DIR = root / "index"
        ac.MANIFEST = root / "index" / "manifest.yaml"
        validate.ROOT, validate.INDEX_DIR, validate.MANIFEST = (
            root, ac.INDEX_DIR, ac.MANIFEST)
        find.ALIASES_FILE = root / "index" / "aliases.yaml"
        try:
            yield root
        finally:
            for (module, name), value in saved.items():
                setattr(module, name, value)


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def has(issues: list[str], *needle: str) -> bool:
    """Хотя бы одна проблема содержит все подстроки сразу (а не «одна из»)."""
    return any(all(n in issue for n in needle) for issue in issues)


class ClassifyTest(unittest.TestCase):
    """Вердикты раннеров: по ним CI решает, жива запись или мертва."""

    def test_ok(self):
        self.assertEqual(vs.classify(0, ""), ("ok", ""))

    def test_fmt_breaks_ci(self):
        # Код из библиотеки копируют как есть: «почти оформлен» = тот же баг.
        verdict, note = vs.classify(0, "AC:FMT\nmain.go")
        self.assertEqual(verdict, "fmt")
        self.assertIn("gofmt", note)

    def test_deps_is_not_fail(self):
        for out in ("no required module provides package example.com/x",
                    # tsc — с заглавной: тот же случай «модуля нет», а не «код битый»
                    "block.tsx(5,25): error TS2307: Cannot find module './subject'"):
            with self.subTest(out=out[:30]):
                self.assertEqual(vs.classify(1, out)[0], "deps")

    def test_fail_keeps_first_line(self):
        verdict, note = vs.classify(1, "x.go:3:2: undefined: foo\nsecond line")
        self.assertEqual((verdict, note), ("fail", "x.go:3:2: undefined: foo"))

    def test_traceback_keeps_last_line(self):
        out = "Traceback (most recent call last):\n  File \"a.py\", line 1\nValueError: boom"
        self.assertEqual(vs.classify(1, out)[1], "ValueError: boom")

    def test_service_noise_ignored(self):
        self.assertEqual(vs.classify(1, "# comment\nreal error")[1], "real error")


class AcParseTest(unittest.TestCase):
    def test_frontmatter(self):
        with temp_repo() as root:
            self.assertEqual(ac.parse_frontmatter(root / "go/snippets/x.md")["id"], "go-x")
            write(root, "note.md", "просто текст без frontmatter\n")
            self.assertIsNone(ac.parse_frontmatter(root / "note.md"))
            write(root, "closed.md", "---\nid: a\n")  # закрывающего разделителя нет
            self.assertIsNone(ac.parse_frontmatter(root / "closed.md"))

    def test_code_fences_only_known_langs(self):
        text = "```go\npackage a\n```\n```sql\nSELECT 1\n```\n```text\nнет\n```\n"
        self.assertEqual(ac.code_fences(text), {"go", "sql"})

    def test_fence_blocks_pairs(self):
        text = "```go\npackage a\n```\n```sql\nSELECT 1;\n```\n"
        self.assertEqual(ac.fence_blocks(text), [("go", "package a"), ("sql", "SELECT 1;")])
        self.assertEqual(ac.fence_blocks(text, {"sql"}), [("sql", "SELECT 1;")])

    def test_needs_frontmatter(self):
        with temp_repo() as root:
            self.assertTrue(ac.needs_frontmatter(root / "go/snippets/x.md"))
            for rel in ("README.md", "docs/FORMAT.md", "skills/x/SKILL.md"):
                self.assertFalse(ac.needs_frontmatter(root / rel), rel)

    def test_index_entries_section_path(self):
        with temp_repo():
            entries = ac.index_entries()
            self.assertEqual([str(s) for s, _ in entries], ["go/snippets"])
            self.assertEqual(entries[0][1]["id"], "go-x")


class TextCheckTest(unittest.TestCase):
    def test_clean_repo_has_no_issues(self):
        with temp_repo():
            self.assertEqual(validate.check_text(), [])

    def test_cjk(self):
        with temp_repo() as root:
            write(root, "go/snippets/x.md", CLEAN_FM + "\n中文\n")
            self.assertTrue(has(validate.check_text(), "CJK"))

    def test_sticky_layout(self):
        with temp_repo() as root:
            write(root, "go/snippets/x.md", CLEAN_FM + "\nПроверьте batч\nи Кrash тоже\n")
            issues = validate.check_text()
            self.assertEqual(len(issues), 2, issues)  # одна проблема на строку
            self.assertTrue(all("смешение раскладок" in i for i in issues))

    def test_code_and_inline_are_not_prose(self):
        # Примеры опечаток живут в документации и в коде — проверяться не должны.
        with temp_repo() as root:
            write(root, "go/snippets/x.md",
                  CLEAN_FM + "\nВот `batч` — опечатка:\n\n```go\n// batч\n```\n")
            self.assertEqual(validate.check_text(), [])

    def test_line_number_points_at_the_prose(self):
        with temp_repo() as root:
            write(root, "go/snippets/x.md", CLEAN_FM + "\n\nно это Кrash\n")
            rel_line = next(i for i in validate.check_text() if "x.md" in i)
            line = int(rel_line.split(":")[1])
            self.assertEqual((root / "go/snippets/x.md").read_text().splitlines()[line - 1],
                             "но это Кrash")


class StructureCheckTest(unittest.TestCase):
    def test_snippet_requires_choice_sections(self):
        with temp_repo() as root:
            write(root, "go/snippets/x.md", CLEAN_FM.replace("Когда НЕ использовать", "Когда"))
            issues = validate.check_structure()
            self.assertTrue(has(issues, "category=snippet", "Когда НЕ использовать"))
            self.assertFalse(any("Related" in i for i in issues))  # Related на месте

    def test_pattern_needs_less(self):
        with temp_repo() as root:
            write(root, "go/snippets/x.md",
                  CLEAN_FM.replace("category: snippet", "category: pattern")
                  .replace("**Когда НЕ использовать** — кратко.\n", ""))
            self.assertEqual(validate.check_structure(), [])


class FrontmatterCheckTest(unittest.TestCase):
    def test_clean(self):
        with temp_repo():
            self.assertEqual(validate.check_frontmatter(), [])

    def test_missing_field_and_bad_values(self):
        with temp_repo() as root:
            write(root, "go/snippets/x.md",
                  CLEAN_FM.replace("status: stable", "status: gtd")
                  .replace("tags: [http, context, client]", "tags: [429]"))
            issues = validate.check_frontmatter()
            self.assertTrue(has(issues, "status", "не в списке"), issues)
            self.assertTrue(has(issues, "tags", "списком строк"), issues)

    def test_duplicate_id(self):
        with temp_repo() as root:
            write(root, "go/snippets/y.md", CLEAN_FM.replace("# Go X", "# Go Y"))
            self.assertTrue(has(validate.check_frontmatter(), "дубликат id"))

    def test_bad_id_prefix(self):
        with temp_repo() as root:
            write(root, "go/snippets/x.md", CLEAN_FM.replace("id: go-x", "id: rust-x"))
            self.assertTrue(has(validate.check_frontmatter(), "известного префикса"))


class ManifestCheckTest(unittest.TestCase):
    def test_clean(self):
        with temp_repo():
            self.assertEqual(validate.check_manifest(), [])

    def test_tags_drift(self):
        with temp_repo() as root:
            write(root, "go/snippets/x.md",
                  CLEAN_FM.replace("tags: [http, context, client]",
                                   "tags: [http, context, client, retry]"))
            self.assertTrue(has(validate.check_manifest(), "tags=", "!= frontmatter"))

    def test_file_missing_from_catalog(self):
        with temp_repo() as root:
            write(root, "go/snippets/y.md",
                  CLEAN_FM.replace("id: go-x", "id: go-y").replace("# Go X", "# Go Y"))
            self.assertTrue(has(validate.check_manifest(), "отсутствует в каталоге"))

    def test_verified_none_with_code(self):
        with temp_repo() as root:
            write(root, "index/go.yaml",
                  CLEAN_INDEX.replace("verified: compiled", "verified: none"))
            self.assertTrue(has(validate.check_manifest(), "verified=none", "есть код"))

    def test_unknown_path(self):
        with temp_repo() as root:
            write(root, "index/go.yaml", CLEAN_INDEX.replace("go/snippets/x.md",
                                                             "go/snippets/gone.md"))
            self.assertTrue(has(validate.check_manifest(), "путь", "не существует"))

    def test_section_file_must_be_listed(self):
        with temp_repo() as root:
            write(root, "index/shared.yaml", "concepts: []\n")
            self.assertTrue(has(validate.check_manifest(), "отсутствует в sections"))


class AliasesCheckTest(unittest.TestCase):
    ALIAS = "aliases:\n  upsert: [go-x]\n"

    def test_clean(self):
        with temp_repo(**{"index/aliases.yaml": self.ALIAS}):
            self.assertEqual(validate.check_aliases(), [])

    def test_missing_file_is_fine(self):
        with temp_repo():
            self.assertEqual(validate.check_aliases(), [])

    def test_all_four_rules(self):
        with temp_repo(**{"index/aliases.yaml": (
                self.ALIAS
                + "  Dead lock: [go-x]\n"      # форма ключа
                + "  http: [go-x]\n"           # уже тег
                + "  deadlock: [no-such]\n"    # нет такой записи
                + "  empty: []\n")}):          # пустой список
            issues = validate.check_aliases()
            self.assertEqual(len(issues), 4, issues)
            self.assertTrue(has(issues, "не в форме тега"))
            self.assertTrue(has(issues, "уже тег или id"))
            self.assertTrue(has(issues, "no-such"))
            self.assertTrue(has(issues, "непустой список"))

    def test_broken_yaml_reported(self):
        with temp_repo(**{"index/aliases.yaml": "aliases: ["}):
            self.assertTrue(has(validate.check_aliases(), "невалидный YAML"))

    def test_not_a_mapping(self):
        with temp_repo(**{"index/aliases.yaml": "aliases:\n  - go-x\n"}):
            self.assertTrue(has(validate.check_aliases(), "со словарём"))


class FindTest(unittest.TestCase):
    """Порядок выдачи важнее самого факта находки: агент читает первые строки."""

    # Поиск читает каталог, а не frontmatter: фикстура — index/*.yaml.
    TWO = """snippets:
  - id: go-x
    title: Go X
    path: go/snippets/x.md
    tags: [rate-limit, http, client]
    status: stable
    verified: compiled
    updated: 2026-01-01
  - id: go-aa
    title: "HTTP: пул соединений"
    path: go/snippets/x.md
    tags: [pool, db, client]
    status: stable
    verified: compiled
    updated: 2026-01-01
"""
    FIXTURE = {"index/go.yaml": TWO, "index/aliases.yaml": "aliases:\n  upsert: [go-x]\n"}

    def test_normalize_and_forms(self):
        self.assertEqual(find.normalize("Rate_Limit"), "rate-limit")
        self.assertEqual(find.forms("HTTP  Client"), ["http client", "http-client"])
        self.assertEqual(find.forms("rate-limit"), ["rate-limit"])
        self.assertEqual(find.forms("  "), [])

    def test_exact_tag_outranks_title(self):
        with temp_repo(**self.FIXTURE):
            hits = find.find("http")
            self.assertEqual([h["id"] for h in hits], ["go-x", "go-aa"])
            self.assertEqual([h["score"] for h in hits], [100, 40])

    def test_hyphen_and_space_forms_meet(self):
        with temp_repo(**self.FIXTURE):
            self.assertEqual(find.find("rate limit")[0]["score"], 100)
            self.assertEqual(find.find("Rate_Limit")[0]["score"], 100)

    def test_alias_adds_record_by_foreign_word(self):
        with temp_repo(**self.FIXTURE):
            hits = find.find("upsert")
            self.assertEqual([h["id"] for h in hits], ["go-x"])
            self.assertEqual(hits[0]["score"], 80)
            self.assertEqual(find.find("no-such-word"), [])

    def test_section_filter(self):
        with temp_repo(**self.FIXTURE):
            self.assertEqual([h["id"] for h in find.find("upsert", "shared")], [])
            self.assertEqual([h["id"] for h in find.find("http", "go")], ["go-x", "go-aa"])
            self.assertEqual([h["id"] for h in find.find("http", "go/snippets")],
                             ["go-x", "go-aa"])

    def test_ties_sorted_by_id(self):
        with temp_repo(**self.FIXTURE):
            self.assertEqual([h["id"] for h in find.find("client")], ["go-aa", "go-x"])

    def test_empty_query_returns_catalog(self):
        with temp_repo(**self.FIXTURE):
            self.assertEqual([h["score"] for h in find.find("")], [0, 0])


class CountFormTest(unittest.TestCase):
    def test_russian_forms(self):
        self.assertEqual(readme.count_form(1, "snippet"), "1 сниппет")
        self.assertEqual(readme.count_form(2, "snippet"), "2 сниппета")
        self.assertEqual(readme.count_form(5, "snippet"), "5 сниппетов")
        self.assertEqual(readme.count_form(11, "snippet"), "11 сниппетов")
        self.assertEqual(readme.count_form(21, "pattern"), "21 паттерн")
        self.assertEqual(readme.count_form(0, "concept"), "0 концепций")


if __name__ == "__main__":
    unittest.main(verbosity=2)
