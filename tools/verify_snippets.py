#!/usr/bin/env python3
"""Прогон код-блоков записей через реальные тулчейны в Docker.

Назначение: `verified` в каталоге `index/` должен отражать факт проверки, а не
обещание. Скрипт достаёт код-блоки из записей и прогоняет их в контейнерах.

Использование:
  python3 tools/verify_snippets.py                     # все поддерживаемые языки
  python3 tools/verify_snippets.py --lang go,ts        # только эти языки
  python3 tools/verify_snippets.py --section go --jobs 8
  python3 tools/verify_snippets.py --record go-http-client
  python3 tools/verify_snippets.py --json              # машиночитаемый вывод
  python3 tools/verify_snippets.py --table             # что проверяет каждый раннер

Гранулярность: go собирается пакетом на запись (блоки одной записи — один модуль,
соседние блоки ссылаются друг на друга), остальные языки — блок за блоком.

Вердикты:
  ok        — тулчейн принял код
  fail      — отверг: код в записи битый или устарел (находка)
  fmt       — формат не выдержан (gofmt переформатирует блок)
  deps      — не хватает пакетов: сгенерированных (grpc stub) или из другой записи
  fragment  — блок не самодостаточен (нет package), проверить нельзя без выдумывания обёрток

Выход: 0 — находок нет, 1 — есть fail, 2 — ошибка запуска.
Первый запуск скачивает образы и греет кэш модулей (несколько минут).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

try:
    import yaml  # noqa: F401  — нужен tools/ac.py
except ImportError:
    print("ОШИБКА: нужен PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

from ac import INDEX_DIR, MANIFEST, ROOT, content_files, fence_blocks  # noqa: E402

FM_UPDATED_RE = re.compile(r"(?s)^(---\n.*?updated: )\d{4}-\d{2}-\d{2}", re.M)
HEAD_UPDATED_RE = re.compile(r"^(updated: )\d{4}-\d{2}-\d{2}", re.M)

GO_MOD_CACHE = "/go/pkg/mod"

# Зависимости ts/tsx-раннера зафиксированы: без пинов том каждый раз нагревался бы
# «свежим latest», и тулчейн уезжал бы вперёд без спроса (TypeScript 7 → 8 сломал бы
# прогон не кода, а сборки). Обновлять вместе с таблицей «Версии» в AGENTS.md.
TS_DEPS = ("typescript@7.0.2 @types/node@26.6.6 zod@4.6.7 vitest@5.1.1 vite@8.3.8"
           " react@19.3.1 @types/react@19.3.0 @types/react-dom@19.3.0"
           " @testing-library/react@16.3.3 @testing-library/user-event@14.6.13"
           " @vitejs/plugin-react@6.3.0")
TS_VOLUME = "ac-tsdeps"
TS_PREPARE = ("npm i --no-audit --no-fund --prefix /build " + TS_DEPS +
              " >/dev/null && cp -a /build/node_modules/. /deps/")
# Проба смотрит на самый поздно добавленный пакет: том из старого набора
# не пройдёт её, и зависимости переставятся.
TS_PROBE = "test -d /deps/@vitejs/plugin-react"
TS_TSC = ["node", "/w/node_modules/typescript/bin/tsc", "--noEmit", "--strict",
          "--target", "es2024", "--lib", "es2024", "--module", "preserve",
          "--moduleResolution", "bundler", "--typeRoots", "/w/node_modules/@types",
          "--types", "node"]
PG_CONTAINER = "ac-verify-pg"
PG_IMAGE = "postgres:18-alpine"
# SQLSTATE «объекта нет»: блок ссылается на схему из соседнего блока. Это deps —
# проверить нельзя, а не сломано.
PG_MISSING = {"42P01", "42703", "42883", "42P02", "42704", "42P10"}
GO_IMPORT = re.compile(r'"example\.com/([^/"]+)')


@dataclass
class Runner:
    """Как проверить один набор файлов: чем прогнать, где кэш зависимостей."""

    lang: str
    image: str
    cmd: list[str]
    what: str = ""                                  # что доказывает прогон (для FORMAT.md)
    mount: str | None = None                        # куда смонтировать том зависимостей
    volume: str | None = None
    prepare: list[str] | None = None
    probe: str = "test -n \"$(ls -A /deps)\""       # том уже прогрет?
    preamble: Callable[[str], str] = lambda t: t    # обрамление блока-фрагмента
    env: dict[str, str] = field(default_factory=dict)
    run_as_host_user: bool = False                  # тулчейн пишет артефакты в монт
    timeout: int = 900

    def run(self, workdir: Path, files: dict[str, str]) -> tuple[str, str]:
        for name, body in files.items():
            target = workdir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")
        args = ["docker", "run", "--rm", "-v", f"{workdir}:/w", "-w", "/w"]
        if self.volume and self.mount:
            args += ["-v", f"{self.volume}:{self.mount}"]
        if self.run_as_host_user:
            # Иначе артефакты сборки остаются root-owned в примонтированном
            # каталоге, и временный каталог с хоста не удалить.
            args += ["-u", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp"]
        for key, value in self.env.items():
            args += ["-e", f"{key}={value}"]
        proc = subprocess.run(args + [self.image, *self.cmd], capture_output=True,
                              text=True, timeout=self.timeout)
        return classify(proc.returncode, proc.stdout + proc.stderr)


GO_SCRIPT = """
set -e
cd /w
if [ -n "$(gofmt -l .)" ]; then echo "AC:FMT"; fi
go build ./... || { go mod tidy; go build ./...; }
"""

# Блок без import/export компилировался бы как скрипт и воевал с globals
# (@types/node объявляет Event, Buffer, …); в реальном файле это модуль.
TS_MODULE = lambda t: t if re.search(r"^\s*(import|export)\b", t, re.M) else "export {};\n" + t
# Фрагмент bash без shebang: shellcheck нужен shell-директива.
BASH_SHELL = lambda t: t if t.startswith("#!") else "# shellcheck shell=bash\n" + t


def pg_server() -> None:
    """Поднять общий проверочный сервер PostgreSQL (один на прогон)."""
    running = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", PG_CONTAINER],
                             capture_output=True, text=True)
    if running.stdout.strip() == "true":
        return
    subprocess.run(["docker", "rm", "-f", PG_CONTAINER], capture_output=True)
    print(f"[подготовка] сервер {PG_CONTAINER} ({PG_IMAGE})…", file=sys.stderr)
    # pg_stat_statements — единственное расширение, на которое ссылается контент;
    # без preload оно не создаётся.
    subprocess.run(["docker", "run", "-d", "--name", PG_CONTAINER,
                    "-e", "POSTGRES_HOST_AUTH_METHOD=trust", PG_IMAGE,
                    "-c", "shared_preload_libraries=pg_stat_statements"], check=True,
                   capture_output=True)
    _pg_wait_ready()


def _pg_wait_ready() -> None:
    """Ждать рабочий сервер, а не временный сервер entrypoint'а.

    docker-entrypoint.sh поднимает postmaster на время initdb, гасит его и только
    потом запускает настоящий. pg_isready проходит и в первой фазе, а psql,
    попавший в её конец, ловит «database system is shutting down» — на CI это
    роняло два SQL-прогона из семи. По логам судить нельзя: строки entrypoint'а
    идут в stdout, строки postmaster'а — в stderr, и в `docker logs` они
    перемешиваются. Поэтому признак простой: время запуска postmaster не
    меняется три проверки подряд (переход временный -> настоящий его меняет).
    """
    prev = None
    same = 0
    for _ in range(90):
        probe = subprocess.run(
            ["docker", "exec", PG_CONTAINER, "psql", "-U", "postgres", "-X", "-Aqt", "-c",
             "SELECT pg_postmaster_start_time()"], capture_output=True, text=True)
        cur = probe.stdout.strip() if probe.returncode == 0 else ""
        same = same + 1 if cur and cur == prev else 0
        if same >= 2:  # три одинаковых отсчёта: t, t+2, t+4
            return
        prev = cur
        time.sleep(2)
    raise RuntimeError("PostgreSQL не перешёл на рабочий сервер за ~180s")


# Сообщения, которые означают «сервер в этот момент переезжал», а не «код битый».
PG_INFRA = ("shutting down", "starting up", "57P01", "57P03", "Connection refused",
            "is not running")


_PG_LOCK = threading.Lock()  # схема одна на сервер: блоки прогоняются по очереди


def run_sql_job(blocks: list[tuple[int, str]]) -> tuple[str, str]:
    with _PG_LOCK:
        for attempt in (0, 1):
            verdict, note = _run_sql(blocks)
            if verdict == "fail" and attempt == 0 and any(m in note for m in PG_INFRA):
                _pg_wait_ready()  # сервер переезжал с временного на рабочий
                continue
            return verdict, note
        return verdict, note


def _run_sql(blocks: list[tuple[int, str]]) -> tuple[str, str]:
    """SQL-блоки записи в одной схеме: CREATE из первого блока годится остальным.

    Схема одна на запись (как один go-модуль), блоки идут по порядку. Первый
    же блок, где что-то упало, определяет вердикт всей записи.
    """
    pg_server()
    reset = subprocess.run(
        ["docker", "exec", PG_CONTAINER, "psql", "-U", "postgres", "-q", "-c",
         "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;\n"
         "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"],
        capture_output=True, text=True, timeout=120)
    if reset.returncode != 0:  # это падение инструмента, а не записи: говорим прямо
        note = (reset.stdout + reset.stderr).strip().splitlines()
        return "fail", "сброс схемы: " + (note[-1][:140] if note else "psql вернул ошибку")
    for i, code in blocks:
        proc = subprocess.run(
            ["docker", "exec", "-i", PG_CONTAINER, "psql", "-U", "postgres", "-X", "-q",
             "-v", "ON_ERROR_STOP=1", "-v", "VERBOSITY=verbose", "-f", "-"],
            input=code, capture_output=True, text=True, timeout=120)
        if proc.returncode == 0:
            continue
        out = proc.stdout + proc.stderr
        note = f"#{i}: " + next((line.strip()[:150] for line in out.splitlines()
                                 if "ERROR" in line), "")
        state = re.search(r"(?:ERROR:\s+|SQLSTATE:\s*)([0-9A-Z]{5})\b", out)
        if state and state.group(1) in PG_MISSING:
            return "deps", note
        return "fail", note
    return "ok", ""


CS_IMAGE = "mcr.microsoft.com/dotnet/sdk:10.0"
# Пакеты, без которых часть блоков не собирается, и признак, по которому они
# подключаются. Версия плавает по строке TFM: закрепление за .NET 10, а не за
# часом публикации пакета (сверяется кварталом, как остальное).
CS_PACKAGES = {
    "openapi": [("Microsoft.AspNetCore.OpenApi", "10.0.*")],
    "resilience": [("Microsoft.Extensions.Http.Resilience", "10.11.*")],
    # Тестовый блок собирается как обычный проект: достаточно xunit (атрибуты и
    # Assert), раннер тест-раннер не запускается.
    "xunit": [("xunit", "2.9.*")],
}
CS_TYPES = re.compile(r"\b(WebApplicationBuilder|WebApplication|Microsoft\.AspNetCore|HttpContext|Results)\b")
# Unity-код собирается только Unity Editor: не нехватка пакета, а отсутствие
# тулчейна (ADR-0005). Такие блоки в прогон не идут — вердикт deps врал бы, что
# дело в зависимостях, и гонял бы dotnet впустую.
CS_UNITY = re.compile(r"\b(UnityEngine|MonoBehaviour|GameObject|ScriptableObject|SerializeField)\b")

CS_PROJECT = """<Project Sdk="{sdk}">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
  <ItemGroup>
    <FrameworkReference Include="Microsoft.AspNetCore.App" />
  </ItemGroup>
{packages}</Project>
"""

# Каждый блок — свой проект: top-level statements и объявления разных видов в
# одном файле не уживаются. Экзешник не собрался из-за отсутствия Main — блок
# состоит из одних объявлений, собираем библиотекой.
CS_SCRIPT = """
set -u
cd /w
fails=""
deps=""
for d in b*/; do
  d=${d%/}
  out=$(dotnet build -v q --nologo "$d/p.csproj" 2>&1) && continue
  case "$out" in
  *"error CS5001"*)
    sed -i "s|<OutputType>Exe</OutputType>|<OutputType>Library</OutputType>|" "$d/p.csproj"
    out=$(dotnet build -v q --nologo "$d/p.csproj" 2>&1) && continue
    ;;
  esac
  # NU* и «нет такого пространства имён» = не хватает пакета: проверить нельзя,
  # а не сломано. Остальное — код в записи.
  case "$out" in
  *" error NU"*|*"error CS0234"*|*"error CS0246"*|*"error CS7069"*)
    [ -n "$deps" ] || deps="$d: $(printf '%s' "$out" | grep -oE '(NU|CS)[0-9]+' | head -n1)"
    ;;
  *)
    [ -n "$fails" ] || fails="$d: $(printf '%s' "$out" | grep -m1 'error C' | sed 's|/w/||' | cut -c1-140)"
    ;;
  esac
done
if [ -n "$fails" ]; then echo "AC:FAIL $fails"; exit 1; fi
if [ -n "$deps" ]; then echo "AC:DEPS $deps"; exit 1; fi
"""


def cs_project_files(blocks: list[tuple[int, str]]) -> dict[str, str]:
    """Запись C# как N проектов: csproj на блок, пакет — только если блок о нём просит."""
    files: dict[str, str] = {"build.sh": CS_SCRIPT}
    for i, code in blocks:
        refs = ""
        for marker, packages in CS_PACKAGES.items():
            if marker in code.lower():
                for package, version in packages:
                    refs += f'    <PackageReference Include="{package}" Version="{version}" />\n'
        files[f"b{i}/p.csproj"] = CS_PROJECT.format(
            sdk="Microsoft.NET.Sdk.Web" if CS_TYPES.search(code) else "Microsoft.NET.Sdk",
            packages=f"  <ItemGroup>\n{refs}  </ItemGroup>\n" if refs else "")
        files[f"b{i}/Program.cs"] = code
    return files

def classify(code: int, out: str) -> tuple[str, str]:
    # Маркеры скриптовых раннеров: что они увидели, решают они сами.
    for marker, verdict in (("AC:FAIL", "fail"), ("AC:DEPS", "deps")):
        if out.startswith(marker) or f"\n{marker}" in out:
            line = next((x for x in out.splitlines() if x.startswith(marker)), marker)
            return verdict, line[len(marker):].strip()[:200]

    lines = [x.strip() for x in out.splitlines()
             if x.strip() and x.strip() != "AC:FMT" and not x.startswith("#")]
    # трейсбек python важнее в последней строке (сама ошибка), а не в первой
    note = lines[-1] if lines and "Traceback" in out else (lines[0] if lines else "")
    if code == 0:
        return ("fmt", "gofmt переформатировал файл") if "AC:FMT" in out else ("ok", "")
    low = out.lower()  # tsc пишет «Cannot find module», go — «cannot find module»
    if "no required module provides" in low or "cannot find module" in low:
        return "deps", note
    return "fail", note


RUNNERS: dict[str, Runner] = {
    "go": Runner(
        "go", "golang:1.27-alpine", ["sh", "/w/run.sh"],
        what="gofmt + go build 1.27 (модуль на запись, кэш модулей в томе ac-gomod)",
        volume="ac-gomod", mount=GO_MOD_CACHE),
    "python": Runner(
        "python", "python:3.14-slim",
        ["python", "-c",
         "import sys; compile(open(sys.argv[1], encoding='utf-8').read(), 'block.py', 'exec')",
         "/w/block.py"],
        what="compile(): синтаксис Python 3.14 (импорты третьих сторон не разрешаются)"),
    "ts": Runner(
        "ts", "node:22-slim", TS_TSC + ["/w/block.ts"],
        what="tsc 7.0 --noEmit --strict --lib es2024 (typescript, @types/node, zod, vitest,"
             " react, Testing Library — том ac-tsdeps)",
        volume=TS_VOLUME, mount="/w/node_modules",
        prepare=["sh", "-c", TS_PREPARE],
        probe=TS_PROBE,
        preamble=TS_MODULE),
    # React-код: те же зависимости, но .tsx, JSX-фабрика и DOM-типы.
    # dom обязателен: без него типы элементов берутся из @types/react/global.d.ts —
    # урезанного набора, где у input нет .value, а ResizeObserver отсутствует;
    # падения выглядят как «код в записи битый», хотя дело в конфигурации прогона.
    "tsx": Runner(
        "tsx", "node:22-slim",
        ["node", "/w/node_modules/typescript/bin/tsc", "--noEmit", "--strict",
         "--target", "es2024", "--lib", "es2024,dom", "--module", "preserve",
         "--moduleResolution", "bundler", "--typeRoots", "/w/node_modules/@types",
         "--types", "node", "--jsx", "react-jsx", "/w/block.tsx"],
        what="tsc 7.0 --noEmit --strict --lib es2024,dom --jsx react-jsx (react 19,"
             " @types/react, @testing-library/react — том ac-tsdeps)",
        volume=TS_VOLUME, mount="/w/node_modules",
        prepare=["sh", "-c", TS_PREPARE],
        probe=TS_PROBE,
        preamble=TS_MODULE),
    "js": Runner("js", "node:22-slim", ["node", "--check", "/w/block.js"],
                 what="node --check: синтаксис JS"),
    "bash": Runner("bash", "koalaman/shellcheck-alpine:latest",
                   ["shellcheck", "-f", "gcc", "/w/block.sh"],
                   what="shellcheck -f gcc (код 0 = замечаний нет)",
                   preamble=BASH_SHELL),
    "sh": Runner("sh", "koalaman/shellcheck-alpine:latest",
                 ["shellcheck", "-f", "gcc", "/w/block.sh"],
                 what="shellcheck -f gcc", preamble=BASH_SHELL),
    "c": Runner("c", "gcc:14-bookworm",
                ["gcc", "-std=c23", "-fsyntax-only", "-Wall", "-Wextra", "/w/block.c"],
                what="gcc -std=c23 -fsyntax-only -Wall -Wextra"),
    # SQL исполняется не «в контейнере блока», а на общем сервере (см. run_sql_job):
    # image здесь — образ того сервера.
    "csharp": Runner(
        "csharp", CS_IMAGE, ["sh", "/w/build.sh"],
        what="dotnet build 10.0: проект на блок, Exe с падением на Library для блоков "
             "без точки входа, FrameworkReference AspNetCore, NuGet по признаку блока",
        env={"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1",
             "DOTNET_CLI_HOME": "/tmp", "NUGET_PACKAGES": "/tmp/nuget"},
        run_as_host_user=True, timeout=1800),
    "sql": Runner("sql", PG_IMAGE, [],
                  what="psql на PostgreSQL 18: блок выполняется в чистой схеме; "
                       "ссылки на таблицы из чужих блоков — deps, не fail"),
}
# Имя файла, в который кладётся блок (go собирается иначе — см. go_files).
FNAME = {"sql": "block.sql", "python": "block.py", "ts": "block.ts", "tsx": "block.tsx",
         "js": "block.js", "bash": "block.sh", "sh": "block.sh", "c": "block.c"}
PACKAGE_RE = re.compile(r"^package\s+(\w+)", re.M)


@dataclass
class Job:
    path: str
    rid: str
    lang: str
    blocks: list[int]
    files: dict[str, str] = field(default_factory=dict)
    codes: list[tuple[int, str]] = field(default_factory=list)   # go: сборка на запись
    result: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.path}#{'+'.join(str(b) for b in self.blocks)}"


def go_module_files(blocks: list[tuple[int, str]], isolated: bool = False) -> dict[str, str]:
    """Собрать запись в один go-модуль: module — из импортов, каталоги — по импортам.

    isolated=True — каждый блок в своём каталоге: так собирают «варианты одного
    пакета», которые переопределяют типы друг друга в одном каталоге.
    """
    texts = [c for _, c in blocks]
    mods = [m.group(1) for _, c in blocks for m in [GO_IMPORT.search(c)] if m]
    mod = f"example.com/{mods[0]}" if mods else "example.com/ac"
    pkgs = {m.group(1) for _, c in blocks for m in [PACKAGE_RE.search(c)] if m}
    files: dict[str, str] = {"go.mod": f"module {mod}\n\ngo 1.27\n"}
    for i, code in blocks:
        pkg = PACKAGE_RE.search(code).group(1)
        dir_ = f"b{i}/" if isolated else ""
        if isolated:
            files[f"{dir_}block.go"] = code
            continue
        for t in texts:                     # каталог — по импорту, который на него ссылается
            m = re.search(rf'"({re.escape(mod)}/(?:[^"]*/)?{pkg})"', t)
            if m:
                dir_ = m.group(1)[len(mod) + 1:] + "/"
                break
        else:
            dir_ = f"{pkg}/" if len(pkgs) > 1 else ""
        files[f"{dir_}block{i}.go"] = code
    return files


def collect(langs: list[str], section: str | None, record: str | None) -> list[Job]:
    jobs: list[Job] = []
    for path in content_files():
        rel = str(path.relative_to(ROOT))
        if section and not rel.startswith(section + "/"):
            continue
        text = path.read_text(encoding="utf-8")
        m = re.search(r"^id: (\S+)", text, re.M)
        rid = m.group(1) if m else rel
        if record and rid != record:
            continue
        by_lang: dict[str, list[tuple[int, str]]] = {}
        for i, (lang, code) in enumerate(fence_blocks(text, set(langs)), 1):
            by_lang.setdefault(lang, []).append((i, code))
        for lang, blocks in by_lang.items():
            if lang == "go":
                for i, code in blocks:
                    if not PACKAGE_RE.search(code):
                        jobs.append(Job(rel, rid, lang, [i], {},
                                        result={"verdict": "fragment",
                                                "note": "нет объявления package"}))
                whole = [(i, c) for i, c in blocks if PACKAGE_RE.search(c)]
                if whole:
                    jobs.append(Job(rel, rid, lang, [i for i, _ in whole], codes=whole))
            elif lang == "sql":
                if blocks:
                    jobs.append(Job(rel, rid, lang, [i for i, _ in blocks], codes=blocks))
            elif lang == "csharp":
                checkable = [(i, c) for i, c in blocks if not CS_UNITY.search(c)]
                if checkable:
                    jobs.append(Job(rel, rid, lang, [i for i, _ in checkable], codes=checkable))
            else:
                for i, code in blocks:
                    jobs.append(Job(rel, rid, lang, [i], {FNAME[lang]: RUNNERS[lang].preamble(code)}))
    return jobs


# Не код, а оформление: их отсутствие раннера — не пробел в покрытии.
NOT_CODE = {"", "text", "console", "diff", "markdown"}


def present_langs() -> set[str]:
    langs: set[str] = set()
    for path in content_files():
        for lang, _ in fence_blocks(path.read_text(encoding="utf-8"), None):
            if lang not in NOT_CODE:
                langs.add(lang)
    return langs


def prepare_volumes(runners: list[Runner]) -> None:
    for r in runners:
        if not (r.volume and r.prepare):
            continue
        probe = subprocess.run(
            ["docker", "run", "--rm", "-v", f"{r.volume}:/deps", r.image, "sh", "-c", r.probe],
            capture_output=True)
        if probe.returncode == 0:
            continue
        print(f"[подготовка] том {r.volume}: ставлю зависимости…", file=sys.stderr)
        subprocess.run(["docker", "run", "--rm", "-v", f"{r.volume}:/deps",
                        r.image, *r.prepare], check=True)


def run_job(job: Job) -> Job:
    if job.result:
        return job
    if job.lang == "sql":
        job.result = {"verdict": "fail", "note": ""}
        try:
            verdict, note = run_sql_job(job.codes)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, RuntimeError) as e:
            verdict, note = "fail", str(e)[:160]
        job.result = {"verdict": verdict, "note": note[:200]}
        return job

    runner = RUNNERS[job.lang]

    def go_runsh(d: Path) -> None:
        (d / "run.sh").write_text(GO_SCRIPT, encoding="utf-8")

    if job.lang == "csharp":
        runner = RUNNERS[job.lang]
        try:
            with tempfile.TemporaryDirectory(prefix="acv-") as tmp:
                verdict, note = runner.run(Path(tmp), cs_project_files(job.codes))
        except subprocess.TimeoutExpired:
            verdict, note = "fail", "timeout 900s"
        except subprocess.CalledProcessError as e:
            verdict, note = "fail", str(e)[:160]
        job.result = {"verdict": verdict, "note": note[:200]}
        return job

    with tempfile.TemporaryDirectory(prefix="acv-") as tmp:
        d = Path(tmp)
        files = job.files
        if job.lang == "go":
            go_runsh(d)
            files = go_module_files(job.codes)
        try:
            verdict, note = runner.run(d, files)
            if job.lang == "go" and verdict == "fail" and (
                    "redeclared" in note or "found packages" in note):
                # варианты одного пакета в одной записи: собрать каждый отдельно
                shutil.rmtree(d, ignore_errors=True)
                d.mkdir()
                go_runsh(d)
                verdict, note = runner.run(d, go_module_files(job.codes, isolated=True))
                note = "варианты одного пакета, собраны отдельно; " + note
        except subprocess.TimeoutExpired:
            verdict, note = "fail", "timeout 900s"
        except subprocess.CalledProcessError as e:
            verdict, note = "fail", str(e)[:160]
    job.result = {"verdict": verdict, "note": note[:200]}
    return job


def _entry_span(lines: list[str], rel: str) -> tuple[int, int] | None:
    """Границы блока записи каталога с `path: <rel>` (от `- id:` до следующего)."""
    for i, line in enumerate(lines):
        if line.strip() != f"path: {rel}":
            continue
        start = i
        while start > 0 and not lines[start].lstrip().startswith("- id:"):
            start -= 1
        end = i + 1
        while end < len(lines) and not lines[end].lstrip().startswith("- id:"):
            end += 1
        return start, end
    return None


def _entry_patch(text: str, rel: str, fields: dict[str, str]) -> tuple[str, bool]:
    """Проставить поля записи каталога. Возвращает (текст, менялось ли)."""
    lines = text.splitlines(keepends=True)
    span = _entry_span(lines, rel)
    if span is None:
        return text, False
    changed = False
    for j in range(*span):
        for field, value in fields.items():
            if lines[j].lstrip().startswith(f"{field}:"):
                new = re.sub(rf"^(\s*{field}: ).*$", rf"\g<1>{value}", lines[j])
                if new != lines[j]:
                    lines[j] = new
                    changed = True
    return "".join(lines), changed


def _entry_value(text: str, rel: str, field: str) -> str | None:
    lines = text.splitlines(keepends=True)
    span = _entry_span(lines, rel)
    if span is None:
        return None
    for j in range(*span):
        if lines[j].lstrip().startswith(f"{field}:"):
            return lines[j].split(":", 1)[1].strip()
    return None


def fix_index(jobs: list[Job], today: str) -> list[str]:
    """Поднять `verified` до уровня, доказанного прогоном, и обновить `updated`.

    Уровень только растёт (`executed` не понижается). Запись получает `compiled`,
    если все её проверяемые блоки прошли тулчейн; `fragment` (нет package) не
    мешает — его проверить нельзя в принципе.
    """
    rank = {"none": 0, "reviewed": 1, "compiled": 2, "executed": 3}
    by_path: dict[str, list[str]] = {}
    for j in jobs:
        by_path.setdefault(j.path, []).append(j.result["verdict"])
    changed: list[str] = []
    for path, verdicts in sorted(by_path.items()):
        checkable = [v for v in verdicts if v != "fragment"]
        if not checkable or any(v != "ok" for v in checkable):
            continue
        target = ROOT / path
        idx_file = INDEX_DIR / f"{Path(path).parts[0]}.yaml"
        fm_text = target.read_text(encoding="utf-8")
        if not idx_file.exists() or "updated:" not in fm_text:
            continue
        text = idx_file.read_text(encoding="utf-8")
        current = _entry_value(text, path, "verified")
        if current not in rank or rank[current] >= rank["compiled"]:
            continue
        text, was = _entry_patch(text, path, {"verified": "compiled", "updated": today})
        if not was:
            continue
        idx_file.write_text(text, encoding="utf-8")
        target.write_text(FM_UPDATED_RE.sub(lambda m: m.group(1) + today, fm_text, count=1),
                          encoding="utf-8")
        changed.append(path)
    if changed:
        head = MANIFEST.read_text(encoding="utf-8")
        MANIFEST.write_text(HEAD_UPDATED_RE.sub(lambda m: m.group(1) + today, head, count=1),
                            encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("Вердикты")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lang", default=",".join(RUNNERS), help="языки через запятую")
    parser.add_argument("--section", help="префикс пути записи (go, shared, …)")
    parser.add_argument("--record", help="одна запись по id")
    parser.add_argument("--jobs", type=int, default=6, help="параллельных контейнеров")
    parser.add_argument("--json", action="store_true", help="машиночитаемый вывод")
    parser.add_argument("--fix-index", action="store_true",
                        help="поднять verified/updated в index/ по итогам прогона")
    parser.add_argument("--table", action="store_true",
                        help="печатать, что проверяет каждый раннер, и выйти")
    args = parser.parse_args()

    if args.table:
        for r in RUNNERS.values():
            print(f"{r.lang:8} {r.what}")
        return 0

    if not shutil.which("docker"):
        print("ОШИБКА: нужен docker", file=sys.stderr)
        return 2

    langs = [x.strip() for x in args.lang.split(",") if x.strip()]
    unknown = set(langs) - set(RUNNERS)
    if unknown:
        print(f"ОШИБКА: нет раннера для языков: {sorted(unknown)}", file=sys.stderr)
        return 2

    jobs = collect(langs, args.section, args.record)
    if not jobs:
        print("нет блоков под указанные фильтры")
        return 0
    prepare_volumes([RUNNERS[x] for x in langs])

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        done = list(pool.map(run_job, jobs))

    if args.fix_index:
        touched = fix_index(done, dt.date.today().isoformat())
        print(f"verified поднят у {len(touched)} записей" +
              (": " + ", ".join(touched) if touched else ""))

    skipped = sorted(present_langs() - set(RUNNERS))
    order = {"fail": 0, "fmt": 1, "deps": 2, "fragment": 3, "ok": 4}
    if args.json:
        print(json.dumps({
            "results": [{"path": j.path, "id": j.rid, "lang": j.lang, "blocks": j.blocks,
                         **j.result} for j in done],
            "unchecked_langs": skipped,
        }, ensure_ascii=False, indent=1))
    else:
        for j in sorted(done, key=lambda j: (order[j.result["verdict"]], j.path, j.blocks)):
            if j.result["verdict"] != "ok":
                print(f"{j.result['verdict']:9} {j.label} [{j.lang}] {j.result['note']}")
        counts: dict[str, int] = {}
        for j in done:
            counts[j.result["verdict"]] = counts.get(j.result["verdict"], 0) + 1
        print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items()))
              + f"  всего={len(done)}")
        if skipped:
            print(f"без раннера (не проверялось): {', '.join(skipped)}")
    # fail — код битый; fmt — блок расходятся с gofmt. Оба ломают сборку:
    # код из библиотеки копируют как есть, «почти отформатированный» не годится.
    return 1 if any(j.result["verdict"] in ("fail", "fmt") for j in done) else 0


if __name__ == "__main__":
    sys.exit(main())
