#!/usr/bin/env python3
"""MCP-сервер каталога awesome-coding (stdio, JSON-RPC 2.0, без зависимостей).

Даёт агенту поиск по репозиторию без клона и без grep: два инструмента —
`search` (по тегу/названию/алиасу) и `get` (текст записи). Ранжирование и
алиасы — общие с `tools/search.py` (см. `tools/find.py`): читается каталог
`index/*.yaml`, а не всё содержимое репо.

Запуск вручную (для проверки):
  printf '%s\\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python3 tools/mcp_server.py

Подключение (pi / любой MCP-клиент):
  pi mcp add -l awesome-coding -- python3 tools/mcp_server.py
или в .pi/mcp.json:
  {"mcpServers": {"awesome-coding": {"command": "python3", "args": ["tools/mcp_server.py"],
   "description": "Поиск по библиотеке сниппетов awesome-coding"}}}
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ac import ROOT, index_entries  # noqa: E402
from find import find as find_entries  # noqa: E402  — ранжирование + алиасы

PROTOCOL = "2024-11-05"
SERVER = {"name": "awesome-coding", "version": "1.1"}
INSTRUCTIONS = (
    "Библиотека сниппетов и правил awesome-coding. search(query, section) — найти "
    "записи по тегу/названию/алиасу, от близких к далёким (section: go, typescript, "
    "python, shared, database, …), get(id) — полный текст записи. Перед копированием кода читайте «Когда "
    "использовать / Когда НЕ использовать» и статус verified."
)

TOOLS = [
    {
        "name": "search",
        "description": "Поиск записей awesome-coding по тегу или названию.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                            "description": "тег, подстрока названия или алиас (upsert, deadlock, …)"},
                "section": {"type": "string",
                            "description": "раздел: go, typescript, python, shared, database, …"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get",
        "description": "Текст записи по её id (например go-http-client).",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
]


def get(rid: str) -> str:
    for _, entry in index_entries():
        if entry.get("id") == rid.strip():
            path = ROOT / entry["path"]
            if not path.exists():
                return f"запись {rid}: файл {entry['path']} не найден"
            return (f"# {entry.get('title')}\n"
                    f"path: {entry['path']}  status: {entry.get('status')}  "
                    f"verified: {entry.get('verified')}\n\n"
                    + re.sub(r"^---\n.*?\n---\n", "", path.read_text(encoding="utf-8"),
                             count=1, flags=re.S))
    known = ", ".join(sorted(e["id"] for _, e in index_entries())[:10])
    return f"записи {rid!r} нет. первые id: {known}, …"


def call_tool(name: str, args: dict) -> str:
    if name == "search":
        hits = find_entries(args.get("query", ""), args.get("section"))
        if not hits:
            return "ничего не найдено; попробуйте другой тег или section"
        return "\n".join(
            f"{h['id']} — {h['title']} — {h['path']} — "
            f"status={h['status']} verified={h['verified']} tags={h['tags']}"
            for h in hits)
    if name == "get":
        return get(args.get("id", ""))
    raise ValueError(f"неизвестный инструмент: {name}")


def handle(req: dict) -> dict | None:
    method, rid = req.get("method"), req.get("id")
    if method == "initialize":
        return reply(rid, {"protocolVersion": PROTOCOL,
                           "capabilities": {"tools": {}},
                           "serverInfo": SERVER, "instructions": INSTRUCTIONS})
    if method == "ping":
        return reply(rid, {})
    if method == "tools/list":
        return reply(rid, {"tools": TOOLS})
    if method == "tools/call":
        params = req.get("params") or {}
        try:
            body = call_tool(params.get("name", ""), params.get("arguments") or {})
            return reply(rid, {"content": [{"type": "text", "text": body}],
                               "isError": False})
        except Exception as e:  # клиенту — текст ошибки, а не обвал соединения
            return reply(rid, {"content": [{"type": "text", "text": f"ошибка: {e}"}],
                               "isError": True})
    if method in {"resources/list", "prompts/list"}:
        return reply(rid, {method.split("/")[0]: []})
    if method and method.startswith("notifications/"):
        return None
    return error(rid, -32601, f"метод не поддерживается: {method}")


def reply(rid, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def error(rid, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            out = error(None, -32700, f"невалидный JSON: {e}")
        else:
            out = handle(req)
        if out is not None:
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
