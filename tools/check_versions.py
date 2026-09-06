#!/usr/bin/env python3
"""Сверка закреплённых версий (таблица «Версии» в AGENTS.md) с актуальными.

Запросы:
  Go          — go.dev/dl
  Python      — endoflife.date
  C# (.NET)   — builds.dotnet.microsoft.com (release-metadata)
  Kotlin      — maven-metadata (kotlin-stdlib)
  TypeScript  — npm registry
  PostgreSQL  — endoflife.date
  Redis       — GitHub releases (redis/redis)
  Kafka       — GitHub releases (apache/kafka)
  RabbitMQ    — GitHub releases (rabbitmq/rabbitmq-server)
Остальные (JavaScript/ES, C, Bash, Unity) — «н/д»: проверяйте вручную.

Запуск: make check-versions (нужна сеть).
Exit code: 0 — всегда (информационный отчёт); устаревшие версии помечаются ⚠️.
"""

from __future__ import annotations

import json
import re
import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"
TIMEOUT = 15
UA = {"User-Agent": "awesome-coding-version-check/1.0"}

# CA-бандл: certifi, если есть (портативно), иначе системные доверенные.
try:
    import certifi

    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()


def get_json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CTX) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_text(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CTX) as resp:
        return resp.read().decode("utf-8")


def parse_pinned() -> list[tuple[str, str]]:
    """Таблица «Версии» из AGENTS.md: [(технология, закреплённая версия), ...]."""
    text = AGENTS.read_text(encoding="utf-8")
    section = text.split("## Версии", 1)[1].split("\n## ", 1)[0]
    out: list[tuple[str, str]] = []
    for line in section.splitlines():
        m = re.match(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", line)
        if not m or m.group(1) in ("Технология", "---") or set(m.group(1)) <= {"-"}:
            continue
        tech, version = m.group(1), m.group(2)
        vm = re.search(r"\d+(?:\.\d+)*", version)
        if vm:
            out.append((tech, vm.group(0)))
    return out


def current_version(tech: str, pinned: str) -> str | None:
    try:
        if tech == "Go":
            data = get_json("https://go.dev/dl/?mode=json")
            for row in data:
                if row.get("stable"):
                    return row["version"].removeprefix("go")
        elif tech in ("Python", "PostgreSQL"):
            # endoflife.date: список циклов (Python) или dict с "cycles" (PostgreSQL).
            data = get_json(f"https://endoflife.date/api/{tech.lower()}.json")
            cycles = data if isinstance(data, list) else data.get("cycles", [])
            for cycle in cycles:
                if cycle.get("latest"):
                    return cycle["latest"]
        elif tech.startswith("C#"):
            major = pinned.split(".")[0]
            data = get_json(
                f"https://builds.dotnet.microsoft.com/dotnet/release-metadata/{major}.0/releases.json"
            )
            return data.get("latest-release")
        elif tech == "Kotlin":
            # <latest> может указывать на RC — берём максимальную СТАБИЛЬную из <versions>.
            meta = get_text(
                "https://repo1.maven.org/maven2/org/jetbrains/kotlin/kotlin-stdlib/maven-metadata.xml"
            )
            versions = re.findall(r"<version>([^<]+)</version>", meta)
            stable = [
                v for v in versions
                if not re.search(r"-(RC|Beta|M|eap|alpha|dev|preview|nightly)", v, re.I)
            ]
            if stable:
                return max(stable, key=version_tuple)
        elif tech == "TypeScript":
            data = get_json("https://registry.npmjs.org/typescript/latest")
            return data.get("version")
        elif tech in ("Redis", "RabbitMQ"):
            repo = {"Redis": "redis/redis", "RabbitMQ": "rabbitmq/rabbitmq-server"}[tech]
            data = get_json(f"https://api.github.com/repos/{repo}/releases?per_page=15")
            for rel in data:
                if not rel.get("prerelease") and rel.get("tag_name"):
                    return rel["tag_name"].lstrip("v")
        elif tech == "Kafka":
            # GitHub releases у Kafka нет — каталог Apache-архива.
            html = get_text("https://archive.apache.org/dist/kafka/")
            dirs = re.findall(r'href="(\d+\.\d+)/"', html)
            if dirs:
                return max(dirs, key=version_tuple)
    except Exception as e:  # сеть/формат — не роняем отчёт
        print(f"  (запрос не удался: {type(e).__name__}: {str(e).splitlines()[0][:80]})")
    return None


def version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:4])


def main() -> int:
    pinned = parse_pinned()
    if not pinned:
        print("таблица версий в AGENTS.md не найдена", file=sys.stderr)
        return 1

    stale: list[str] = []
    print(f"{'Технология':<12} {'Закреплено':<10} {'Актуальная':<12} Статус")
    print("-" * 52)
    for tech, pinned_v in pinned:
        cur = current_version(tech, pinned_v)
        if cur is None:
            print(f"{tech:<12} {pinned_v:<10} {'н/д':<12} — ручная проверка")
            continue
        p = version_tuple(pinned_v)
        c = version_tuple(cur)[: len(p)]
        if c > p:
            print(f"{tech:<12} {pinned_v:<10} {cur:<12} ⚠️  есть новая стабильная")
            stale.append(f"{tech}: {pinned_v} → {cur}")
        elif c == p:
            print(f"{tech:<12} {pinned_v:<10} {cur:<12} ✓ актуальна")
        else:
            print(f"{tech:<12} {pinned_v:<10} {cur:<12} ? закреплена новее (проверьте источник)")

    print()
    if stale:
        print("⚠️  Устаревшие версии (обновите таблицу в AGENTS.md + manifest):")
        for line in stale:
            print(f"  - {line}")
    else:
        print("Все проверяемые версии актуальны.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
