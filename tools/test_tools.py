#!/usr/bin/env python3
"""Тесты туллинга: `make test`. stdlib unittest, отдельных зависимостей нет.

Зачем: туллинг — то, чему доверяет репозиторий. `make validate` зелёный значит
«записи в порядке» только пока сам валидатор не сломался. Гонка в SQL-раннере
упала в CI через два релиза после появления, потому что проверить её было нечем.
Релизный шаг тоже туллинг: правка CHANGELOG через `str.replace` с несовпавшим
якорем не вставляет блок молча, и три релиза так вышли без записи.

Что покрыто: вердикты раннеров, разбор формата (frontmatter, блоки каталога),
вердикты раннеров, разбор формата (frontmatter, блоки каталога), текстовые и
структурные проверки, каталог, алиасы, порядок поиска (в том числе на реальных
формулировках запросов), русские формы счётчика,
MCP-протокол (ответы и stdio-обвязка), шаги релиза. Проверки, которым нужен живой тулчейн или сеть (verify,
check-versions, mermaid), здесь не запускаются.

Запуск: python3 tools/test_tools.py [-v]
"""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ac
import check_versions
import find
import verify_snippets as vs
import mcp_server
import readme
import release
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
        (vs, "ROOT"): vs.ROOT,
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
        vs.ROOT = root
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

    def test_updated_in_future_is_error(self):
        """Дата ставится по коммиту: «свежая» запись с датой из завтра не проходит."""
        from datetime import date, timedelta
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        fm = re.sub(r"updated: [\d-]+", f"updated: {tomorrow}", CLEAN_FM, count=1)
        with temp_repo(**{"go/snippets/x.md": fm}) as root:
            ac.INDEX_DIR.joinpath("go.yaml").write_text(
                f"snippets:\n  - id: go-x\n    title: Go X\n    path: go/snippets/x.md\n"
                f"    tags: [http, context, client]\n    status: stable\n"
                f"    verified: compiled\n    updated: '{tomorrow}'\n", encoding="utf-8")
            self.assertTrue(has(validate.check_frontmatter(), "в будущем"))


class DeclinedCandidatesTest(unittest.TestCase):
    """Решение по кандидатам живёт в AGENTS.md и читается машиной.

    Разбор — регулярка по markdown: ровно тот класс кода, который молча
    перестаёт находить то, что должно находить (CHANGELOG уже терял блоки
    из-за несовпавшего якоря).
    """

    AGENTS = """## Версии

| Технология | Версия | Fallback |
|---|---|---|
| PostgreSQL | 18 (18.6) | 17 |
| Redis | 8 | 8.0 |

## Отклонённые кандидаты

| Технология | Кандидат | Решение | Причина | Пересмотр |
|---|---|---|---|---|
| PostgreSQL | 19 | отклонено 2026-11-24 | мажору 5 дней | 2027-02 |
"""

    def test_declined_is_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AGENTS.md"
            path.write_text(self.AGENTS, encoding="utf-8")
            saved, check_versions.AGENTS = check_versions.AGENTS, path
            try:
                self.assertEqual(check_versions.parse_declined(), {"PostgreSQL": "19"})
                self.assertEqual(check_versions.parse_pinned(),
                                 [("PostgreSQL", "18"), ("Redis", "8")])
            finally:
                check_versions.AGENTS = saved

    def test_candidate_core_ignores_patch_release(self):
        # «19» в таблице против «19.0» в источнике — тот же кандидат
        self.assertEqual(check_versions.core("19"), check_versions.core("19.0"))
        self.assertNotEqual(check_versions.core("4.4"), check_versions.core("4.5"))


class VerifiedClaimsTest(unittest.TestCase):
    """`verified` не может быть выше того, что способно доказать о записи."""

    EXECUTED = CLEAN_INDEX.replace("verified: compiled", "verified: executed")
    SQL_FM = CLEAN_FM.replace("```go\npackage main\n```", "```sql\nselect 1;\n```")
    KOTLIN_FM = (CLEAN_FM.replace("lang: go", "lang: kotlin")
                 .replace("```go\npackage main\n```", "```kotlin\nfun main() {}\n```"))

    def test_executed_needs_a_runner_that_runs_the_block(self):
        """Go в CI собирается, а не выполняется: executed без proof — ложь."""
        with temp_repo(**{"index/go.yaml": self.EXECUTED}):
            self.assertTrue(has(validate.check_verified_claims(),
                                "verified=executed", "proof:"))

    def test_executed_passes_when_the_run_is_described(self):
        fm = CLEAN_FM.replace("status: stable",
                              'status: stable\nproof: "go run в golang:1.27-alpine, 2026-01-01"')
        with temp_repo(**{"index/go.yaml": self.EXECUTED, "go/snippets/x.md": fm}):
            self.assertEqual(validate.check_verified_claims(), [])

    def test_sql_executed_is_proven_by_ci(self):
        with temp_repo(**{"index/go.yaml": self.EXECUTED, "go/snippets/x.md": self.SQL_FM}):
            self.assertEqual(validate.check_verified_claims(), [])

    UNITY_FM = (CLEAN_FM.replace("lang: go", "lang: csharp")
                .replace("```go\npackage main\n```",
                         "```csharp\nusing UnityEngine;\n"
                         "public class A : MonoBehaviour { }\n```"))
    CS_FM = CLEAN_FM.replace("```go\npackage main\n```",
                             "```csharp\ninternal sealed class P { static void Main() { } }\n```")

    def test_unity_blocks_are_not_proven_by_the_csharp_runner(self):
        """Раннер unity-блоки отбрасывает намеренно: compiled без proof — ложь (issue #7)."""
        with temp_repo(**{"go/snippets/x.md": self.UNITY_FM}):
            self.assertTrue(has(validate.check_verified_claims(),
                                "verified=compiled", "proof:"))

    def test_csharp_blocks_the_runner_takes_are_proven(self):
        """Тот же уровень у записи, чьи блоки раннер действительно берёт."""
        with temp_repo(**{"go/snippets/x.md": self.CS_FM}):
            self.assertEqual(validate.check_verified_claims(), [])

    def test_language_without_runner_needs_proof(self):
        with temp_repo(**{"index/go.yaml": self.EXECUTED.replace("executed", "compiled"),
                          "go/snippets/x.md": self.KOTLIN_FM}):
            self.assertTrue(has(validate.check_verified_claims(), "kotlin", "proof:"))


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
        self.assertEqual(find.forms("HTTP  Client"), ["http client", "http-client", "httpclient"])
        # React-хуки в тегах слитные: «use effect» должна находить тег useeffect
        self.assertIn("useeffect", find.forms("use effect"))
        # дефис из тегов не дублируется, но добавляется слитная форма (useeffect)
        self.assertEqual(find.forms("rate-limit"), ["rate-limit", "ratelimit"])
        self.assertEqual(find.forms("  "), [])

    def test_exact_tag_outranks_title(self):
        with temp_repo(**self.FIXTURE):
            hits = find.find("http")
            self.assertEqual([h["id"] for h in hits], ["go-x", "go-aa"])
            self.assertEqual([h["score"] for h in hits], [100, 40])

    def test_hyphen_and_space_forms_meet(self):
        with temp_repo(**self.FIXTURE):
            # Цифры многословного запроса — сумма слов + вес фразы, поэтому
            # проверяется порядок и то, что дословный тег не обходится словами.
            hits = find.find("rate limit")
            self.assertEqual(hits[0]["id"], "go-x")
            self.assertGreaterEqual(hits[0]["score"], 100)
            self.assertEqual(find.find("Rate_Limit")[0]["id"], "go-x")
            # однословный запрос остаётся на чистой шкале: тег = 100
            self.assertEqual(find.find("rate-limit")[0]["score"], 100)

    def test_words_sum_and_phrase_adds_weight(self):
        """Запрос из двух слов не обязан быть дословным тегом."""
        with temp_repo(**self.FIXTURE):
            both = find.find("http client")[0]["score"]
            one = find.find("http")[0]["score"]
            self.assertGreater(both, one)

    def test_stopwords_do_not_pull_the_catalog(self):
        """Союз «и» — подстрока большинства названий; с ним в выдаче всё подряд."""
        with temp_repo(**self.FIXTURE):
            self.assertEqual(find.tokens("rate limit и"), ["rate", "limit"])
            self.assertEqual(find.tokens("go ci c"), ["go", "ci", "c"])  # латиница короткая — названия
            self.assertEqual(find.tokens("что за час"), ["час"])  # «за» — союз, «час» — слово
            self.assertEqual(find.tokens("и в на"), [])

    def test_word_forms_meet(self):
        self.assertTrue(find.same_stem("клиент", "клиенты"))
        self.assertTrue(find.same_stem("параллельность", "параллельности"))
        self.assertFalse(find.same_stem("час", "часто"))          # короткое слово
        self.assertFalse(find.same_stem("тесты", "тесткомпонента"))  # разная длина
        with temp_repo(**self.FIXTURE):
            # обе записи носят тег client: форма множественного числа не должна
            # обнулять близость ни к одной из них
            hits = find.find("clients")
            self.assertEqual([h["id"] for h in hits], ["go-aa", "go-x"])
            self.assertEqual([h["score"] for h in hits], [60, 60])
            self.assertEqual(find.find("zeitgeber"), [])  # чужое слово близости не даёт

    def test_alias_stacks_with_words(self):
        """Алиас — указатель, он складывается со словами, а не заменяет их."""
        with temp_repo(**self.FIXTURE):
            alone = find.find("upsert")[0]["score"]
            with_word = find.find("upsert http")[0]["score"]
            self.assertEqual(alone, 80)
            self.assertGreater(with_word, alone)

    def test_find_cli_matches_search_cli(self):
        """Молчание find.py агент читает как «записей нет»: вывод один на двоих."""
        tools = Path(find.__file__).resolve().parent
        out = [subprocess.run([sys.executable, str(tools / f), "http"],
                              capture_output=True, text=True).stdout
               for f in ("find.py", "search.py")]
        self.assertEqual(out[0], out[1])
        self.assertIn("go-http-client", out[0])  # subprocess читает настоящий каталог

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


class RealIndexSearchTest(unittest.TestCase):
    """Поиск проверяется формулировками задачи, а не однословными тегами.

    До разбора запроса по словам `make search Q=async` оставался зелёным, пока
    любой запрос из двух слов не давал пустой результат: сравнение было по фразе
    целиком. Формулировки ниже взяты из работы — русские вопросы к латинскому
    словарю тегов, английские фразы, описание проблемы вместо названия записи.

    Ожидание — запись в топ-3: выше ставило бы ранжирование в догму, ниже —
    превращало тест в вечно красный. Где понятие закрыт несколькими записями,
    ожидается любое из списка.
    """

    EXPECTED: list[tuple[str, str | frozenset[str]]] = [
        # русская лексика против латинских тегов
        ("сигнал", "go-graceful-shutdown"),
        ("остановка", "go-graceful-shutdown"),
        ("обработать сигнал остановки", "go-graceful-shutdown"),
        ("отмена", "go-context"),
        ("таймаут", "go-context"),
        ("отменить долгий запрос", "go-context"),
        ("кэш", "database-redis"),
        ("кэш с истечением срока", "database-redis"),
        ("постранично", "database-pagination"),
        ("курсор", "database-pagination"),
        ("миграция", "database-migrations"),
        ("не сломать прода при миграции", "database-migrations"),
        ("индекс", "database-postgres-core"),
        ("транзакция", "database-transactions"),
        ("идемпотентность", "messaging-consumer-groups"),
        ("единовременный запуск", "agenting-lockfile"),
        ("медленные клиенты", "go-websocket"),
        ("переподключение websocket", "go-websocket"),
        ("песочница", "arch-code-sandbox"),
        ("песочница для чужого кода", "arch-code-sandbox"),
        ("секреты", "cicd-secrets"),
        ("докерфайл", "cicd-docker"),
        ("настройки", "shared-configuration"),
        ("конфиг из окружения", "shared-configuration"),
        ("аутентификация", "shared-authentication"),
        ("пароли", "shared-authentication"),
        ("права", "shared-security"),
        ("журнал", "shared-observability"),
        ("метрики", "go-metrics"),
        ("трассировка", "go-tracing"),
        ("распределённая трассировка", "go-tracing"),
        ("автомат состояний", "go-state-machine"),
        ("пул воркеров", "go-worker-pool"),
        ("ограничить параллельность", "go-rate-limit"),
        ("поток токенов", "llm-streaming"),
        ("стриминг", "llm-streaming"),
        ("инструменты модели", "llm-tool-calls"),
        ("тяжёлый виджет", "react-heavy-widget"),
        ("тест компонента", "react-testing"),
        ("чанки", "react-vite"),
        ("проверка вёрстки", "react-ui-check"),
        ("буферизация потока прокси", "go-proxy"),
        # периодическая работа и разбор данных (записи v1.15)
        ("фоновый запуск раз в час", "go-periodic-jobs"),
        ("обновлять кэш по расписанию", "go-periodic-jobs"),
        ("задача каждые 15 минут", "go-periodic-jobs"),
        ("один экземпляр задачи на хосте", "go-periodic-jobs"),
        ("backoff при повторных ошибках", "go-periodic-jobs"),
        ("итог по дням из csv", "py-stdlib-data"),
        ("прочитать выгрузку и посчитать суммы", "py-stdlib-data"),
        ("разобрать дату из строки", "py-stdlib-data"),
        ("прибавить сутки к дате", "py-stdlib-data"),
        ("jsonl журнал событий", "py-stdlib-data"),
        ("хранить деньги без ошибок округления", "py-stdlib-data"),
        # английские формулировки
        ("cache ttl", "database-redis"),
        # про пул соединений пишут две практические записи — нужна любая из них
        ("connection pool", frozenset({"database-postgres-core", "go-sql"})),
        # тег rate-limit носят две записи: ограничитель в Go и gh rate_limit
        ("rate limit", frozenset({"go-rate-limit", "cicd-gh-cli"})),
        ("retry budget", "llm-retries-budget"),
        ("tool calls", "llm-tool-calls"),
        # «медленный клиент» — про несколько записей сразу: websocket, оба http-клиента
        ("slow client", frozenset({"go-websocket", "go-http-client", "csharp-http-client"})),
    ]

    def test_catalog_queries_rank_the_record_high(self):
        for query, want in self.EXPECTED:
            with self.subTest(query=query):
                ids = [h["id"] for h in find.find(query)][:3]
                if isinstance(want, str):
                    self.assertIn(want, ids)
                else:
                    self.assertTrue(want & set(ids), f"ни одной из {sorted(want)} в {ids}")

    def test_practical_record_beats_reference_on_tie(self):
        """«Кэш» — это запись про кэширование, а не таблица решений со словом «кэш»."""
        self.assertEqual(find.find("миграция")[0]["id"], "database-migrations")
        # про кэш говорят заголовки трёх записей — это ничья, и redis обязан быть
        # в первых двух строках, а не первым
        self.assertIn("database-redis", [h["id"] for h in find.find("кэш")][:2])

    def test_no_query_returns_empty_or_all(self):
        """Пустой запрос — это каталог целиком, а не ошибка и не молчание."""
        self.assertEqual(find.find("")[0]["score"], 0)
        self.assertGreater(len(find.find("")), 150)


class CountFormTest(unittest.TestCase):
    def test_russian_forms(self):
        self.assertEqual(readme.count_form(1, "snippet"), "1 сниппет")
        self.assertEqual(readme.count_form(2, "snippet"), "2 сниппета")
        self.assertEqual(readme.count_form(5, "snippet"), "5 сниппетов")
        self.assertEqual(readme.count_form(11, "snippet"), "11 сниппетов")
        self.assertEqual(readme.count_form(21, "pattern"), "21 паттерн")
        self.assertEqual(readme.count_form(0, "concept"), "0 концепций")


class ReleaseTest(unittest.TestCase):
    """Вставка блока CHANGELOG и пин SKILL.md: тихий пропуск недопустим."""

    LOG = "# CHANGELOG\n\nОписание процесса.\n\n## v1.1 — 2026-01-02\n\nСтарый блок.\n"

    def test_insert_before_first_version_block(self):
        out = release.insert_entry(self.LOG, "v1.2", "2026-02-03", "Тело записи.")
        self.assertIn("## v1.2 — 2026-02-03", out)
        self.assertLess(out.index("## v1.2"), out.index("## v1.1"))
        self.assertIn("Старый блок.", out)
        self.assertIn("Описание процесса.", out[:out.index("## v1.2")])

    def test_insert_rejects_duplicates_and_garbage(self):
        with self.assertRaises(ValueError):
            release.insert_entry(self.LOG, "v1.1", "2026-02-03", "есть такой")
        with self.assertRaises(ValueError):
            release.insert_entry(self.LOG, "1.2", "2026-02-03", "версия без v")
        with self.assertRaises(ValueError):
            release.insert_entry(self.LOG, "v1.2", "03.02.2026", "дата не та")
        with self.assertRaises(ValueError):
            release.insert_entry(self.LOG, "v1.2", "2026-02-03", "   ")
        with self.assertRaises(ValueError):
            release.insert_entry("# CHANGELOG\n\nзаголовков версий нет\n", "v1.2", "2026-02-03", "тело")

    def test_patch_release_heading_is_found(self):
        log = "# C\n\n## v1.3.1 — 2026-01-02\n\nx\n"
        out = release.insert_entry(log, "v1.4", "2026-02-03", "новое")
        self.assertLess(out.index("## v1.4"), out.index("## v1.3.1"))

    def test_bump_pin_keeps_comment(self):
        skill = "ac=v1.1                                   # пин версии библиотеки\n"
        out = release.bump_pin(skill, "v1.2")
        self.assertTrue(out.startswith("ac=v1.2"))
        self.assertIn("# пин версии библиотеки", out)

    def test_bump_pin_requires_pin_line(self):
        with self.assertRaises(ValueError):
            release.bump_pin("версии здесь нет\n", "v1.2")

    def test_downgrade_blocked(self):
        with self.assertRaises(ValueError):
            release.bump_pin("ac=v1.12  # пин\n", "v1.9")
        self.assertTrue(release.bump_pin("ac=v1.12  # пин\n", "v1.9",
                                        allow_downgrade=True).startswith("ac=v1.9"))

    def test_patch_bump_is_not_downgrade(self):
        out = release.bump_pin("ac=v1.9  # пин\n", "v1.9.1")
        self.assertTrue(out.startswith("ac=v1.9.1"))

    def test_check_reports_mismatch(self):
        skill = "ac=v1.2  # пин\n"
        log = "# C\n\n## v1.2 — 2026-02-03\n\nтело\n"
        self.assertEqual(release.check(log, skill, "v1.2"), [])
        self.assertTrue(release.check(log, skill, "v1.3"))
        self.assertTrue(release.check(log.replace("## v1.2", "## v1.0"), skill, "v1.2"))
        self.assertTrue(release.check(log, "ac=v1.1\n", "v1.2"))


class CsProjectTest(unittest.TestCase):
    """Сборка C# на запись: sdk по признаку, пакеты по признаку, вердикты скрипта."""

    def test_web_sdk_choosen_by_marker(self):
        files = vs.cs_project_files([
            (1, "var builder = WebApplication.CreateBuilder(args);"),
            (2, "public class Plain { }"),
        ])
        self.assertIn('Sdk="Microsoft.NET.Sdk.Web"', files["b1/p.csproj"])
        self.assertIn('Sdk="Microsoft.NET.Sdk"', files["b2/p.csproj"])
        self.assertNotIn("PackageReference", files["b1/p.csproj"])
        self.assertIn("FrameworkReference", files["b1/p.csproj"])

    def test_packages_added_only_when_needed(self):
        files = vs.cs_project_files([(1, "using Xunit;\nsealed class T { }")])
        self.assertIn('Include="xunit"', files["b1/p.csproj"])
        self.assertNotIn("Resilience", files["b1/p.csproj"])

    def test_script_markers_become_verdicts(self):
        self.assertEqual(vs.classify(1, "AC:DEPS b3: CS0246\n"), ("deps", "b3: CS0246"))
        verdict, note = vs.classify(1, "ok b1\nAC:FAIL b2: b2/Program.cs(1,1): error CS1002\n")
        self.assertEqual(verdict, "fail")
        self.assertIn("CS1002", note)

    def test_unity_code_is_not_built(self):
        """Unity-код собирается только Editor: в csharp-прогон он не идёт."""
        blocks = [(1, "using UnityEngine;\nsealed class P : MonoBehaviour { }"),
                  (2, "var x = 1;")]
        jobs = [b for _, c in blocks if not vs.CS_UNITY.search(c) for b in [c]]
        self.assertEqual(jobs, ["var x = 1;"])

    def test_framework_reference_is_not_deprecated(self):
        """Блок без top-level statements должен собираться Library — скрипт это умеет."""
        self.assertIn("CS5001", vs.CS_SCRIPT)
        self.assertIn("Library", vs.CS_SCRIPT)

class McpTest(unittest.TestCase):
    """MCP-сервер: ответы JSON-RPC и stdio-обвязка. Живой клиент не нужен."""

    def test_initialize_and_tools_list(self):
        init = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertEqual(init["result"]["protocolVersion"], mcp_server.PROTOCOL)
        self.assertEqual(init["result"]["serverInfo"]["name"], "awesome-coding")

        tools = mcp_server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
        self.assertEqual([t["name"] for t in tools], ["search", "get"])
        for tool in tools:
            self.assertEqual(tool["inputSchema"]["type"], "object")
            self.assertTrue(tool["inputSchema"]["required"])

    def test_search_output_is_capped(self):
        """Общий запрос не должен вываливать каталог в контекст агента (issue #8)."""
        body = mcp_server.call_tool("search", {"query": "go"})
        lines = body.splitlines()
        self.assertLessEqual(len(lines), find.LIMIT + 1)
        self.assertIn("ещё", lines[-1])

    def test_empty_query_gets_sections_instead_of_catalog(self):
        body = mcp_server.call_tool("search", {"query": "   "})
        self.assertIn("нужен запрос", body)
        for section in ("go", "react", "llm"):
            self.assertIn(section, body)

    def test_search_and_get_return_text(self):
        hits = mcp_server.call_tool("search", {"query": "http client", "section": "go"})
        self.assertIn("go-http-client", hits)

        body = mcp_server.call_tool("get", {"id": "go-http-client"})
        self.assertIn("path: go/snippets/http-client.md", body)
        self.assertNotIn("id: go-http-client", body)  # frontmatter срезается

    def test_search_without_hits_is_text_not_error(self):
        self.assertIn("не найдено", mcp_server.call_tool("search", {"query": "квантовая-кукуруза"}))

    def test_unknown_tool_is_error_flag_not_exception(self):
        resp = mcp_server.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                  "params": {"name": "нет-такого", "arguments": {}}})
        self.assertTrue(resp["result"]["isError"])
        self.assertIn("неизвестный инструмент", resp["result"]["content"][0]["text"])

    def test_unknown_method_and_notification(self):
        bad = mcp_server.handle({"jsonrpc": "2.0", "id": 4, "method": "resources/templates/list"})
        self.assertEqual(bad["error"]["code"], -32601)
        self.assertIsNone(mcp_server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_stdio_framing_survives_garbage(self):
        """Сервер читает построчно: битая строка не должна ронять соединение."""
        msgs = [
            '{"jsonrpc":"2.0","id":1,"method":"ping"}',
            'это не json',
            '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get","arguments":{"id":"go-http-client"}}}',
        ]
        proc = subprocess.run(
            [sys.executable, str(Path(mcp_server.__file__).resolve())],
            input="\n".join(msgs) + "\n", capture_output=True, text=True, timeout=60)
        replies = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        self.assertEqual(len(replies), 3, proc.stderr)
        self.assertEqual(replies[0]["id"], 1)
        self.assertEqual(replies[1]["error"]["code"], -32700)  # ошибка разбора — ответ, не обвал
        self.assertIn("path:", replies[2]["result"]["content"][0]["text"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
