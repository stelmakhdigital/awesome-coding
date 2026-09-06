# Python

Целевая версия: **Python 3.14** (fallback: 3.13). Закреплено на 2026-09-06.

## Состав раздела

- `README.md` — этот файл (версия, конвенции)
- [rules.md](rules.md) — guardrails (✅/❌)
- [idioms.md](idioms.md) — идиомы (dataclass, match, walrus, contextlib)
- [decisions.md](decisions.md) — таблицы решений (web, HTTP, данные, тесты)
- [snippets/](snippets/) — готовые сниппеты (http-client, error-handling, testing, json, asyncio, web-server)

## Конвенции

- Стиль: PEP 8 + `ruff` (форматтер + линтер в одном).
- Type hints — обязательно для публичного API; проверка `mypy --strict` (или `pyright`).
- Виртуальное окружение: `uv venv` / `venv`; зависимости — `uv` или `pip-tools`.
- Имена: `snake_case` (функции, переменные), `PascalCase` (классы), `UPPER_SNAKE` (константы).
- Исключения: кастомные наследники `Exception`; не ловите «голый» `except:`.
- Файлы: `with open(...)` (context manager) — всегда.

## Инструменты

`ruff`, `mypy`/`pyright`, `pytest`.
