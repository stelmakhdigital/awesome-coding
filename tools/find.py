#!/usr/bin/env python3
"""Поиск по каталогу: нормализация запроса, алиасы, ранжирование.

Общая логика для `tools/search.py` (CLI) и `tools/mcp_server.py` (MCP). Каталог
`index/*.yaml` — источник истины; текст записей не читается (иначе поиск
превращается в grep по всем файлам содержимого, что агент может сделать и сам).

Ранжирование нужно потому, что вывод без порядка заставляет агента читать первые
пять записей подряд, когда первая — точное совпадение тега.

Оценка одного слова против записи:
  100 тег совпал целиком
   70 id совпал целиком
   60 тег содержит слово как подстроку
   55 тег — та же словоформа (same_stem)
   40 слово в названии
   30 слово в названии — та же словоформа
   20 слово в id
Плюс 80, если слово (или форма слова) записано в index/aliases.yaml как имя
этой записи: алиас складывается со словами, а не заменяет их.

Запрос из нескольких слов разбирается по словам: они суммируются, дословное
совпадение всей фразы добавляет +50 поверх, а при равных суммах вперёд идёт та
запись, у которой совпало больше слов. Без этого запрос «медленные клиенты
отвал» не давал ничего, хотя и тег, и название подходящей записи перечисляют эти
понятия: сравнение было по фразе целиком. См. `find`.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

try:
    import yaml  # noqa: F401  — нужен tools/ac.py
except ImportError:
    print("ОШИБКА: нужен PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ac import INDEX_DIR, index_entries  # noqa: E402

ALIASES_FILE = INDEX_DIR / "aliases.yaml"
FIELDS = ("id", "title", "path", "tags", "status", "verified", "updated")


def normalize(term: str) -> str:
    """Каноническая форма тега/алиаса: «Rate Limit», «rate_limit» -> «rate-limit»."""
    return " ".join(term.split()).lower().replace("_", "-").replace(" ", "-")


def forms(query: str) -> list[str]:
    """Формы запроса: раздельно, через дефис и слитно.

    Одно и то же название в заголовке пишется «HTTP client», в тегах —
    «http-client», а хуки React называются слитно — «useeffect». Оставить одну
    форму — значит потерять треть совпадений, поэтому пробираются три и берётся
    лучшая оценка.
    """
    spaced = " ".join(query.split()).lower()
    if not spaced:
        return []
    hyphen = spaced.replace("_", "-").replace(" ", "-")
    glued = hyphen.replace("-", "")
    return list(dict.fromkeys([spaced, hyphen, glued]))


# Союзы и местоимения: с ранжированием по словам они превращаются в мусор —
# «и» входит в большинство названий и тянуло бы в выдачу всё подряд.
STOP = frozenset(
    """в с у на для из и не как что чтобы при по к от до за над под об а но или ещё
    же бы ли этот свой все всё его её мой наш ваш их себя там тут очень раз про
    этом этом""".split()
)


def tokens(query: str) -> list[str]:
    """Значимые слова запроса (союзные — выброшены).

    Короткие кириллические слова — почти всегда предлоги и союзы, а латинские из
    двух букв — названия («go», «ci», «js»), их терять нельзя.
    """
    out = []
    for raw in query.split():
        term = normalize(raw).strip("-")
        if not term or term in STOP:
            continue
        if len(term) < 3 and not term.isascii():
            continue
        out.append(term)
    return list(dict.fromkeys(out))


def same_stem(a: str, b: str) -> bool:
    """Одно ли это слово в разных формах: «клиент»/«клиенты», «миgrant»/«миграции».

    Формы слова расходятся в конце, поэтому сравнивается общее начало: оно должно
    покрывать более короткое слово с точностью до последнего символа. Полное
    совпадение начала не годилось бы («параллельность» и «параллельности»
    расходятся ровно на последней букве), а список окончаний — когда-нибудь
    разъедется со словами репозитория.

    Короткие слова не сравниваются: у «час» и «часто» общее начало есть, а
    понятия разные. Разница в длине ограничена тремя символами: иначе «тесты»
    сходились со слитной формой запроса «тесткомпонента», и это была не форма
    одного слова, а совпадение по началу.
    """
    if min(len(a), len(b)) < 5 or abs(len(a) - len(b)) > 3:
        return False
    return len(os.path.commonprefix([a, b])) >= min(len(a), len(b)) - 1


def aliases() -> dict[str, list[str]]:
    """index/aliases.yaml: слово -> id записей. Файл опционален."""
    if not ALIASES_FILE.exists():
        return {}
    data = yaml.safe_load(ALIASES_FILE.read_text(encoding="utf-8")) or {}
    return {normalize(k): [str(i) for i in v]
            for k, v in (data.get("aliases") or {}).items()}


def wanted_ids(al: dict[str, list[str]], terms: list[str]) -> set[str]:
    """Записи, названные в алиасах любым словом запроса (в любой форме)."""
    out: set[str] = set()
    for key, ids in al.items():
        if any(term == key or term in key or same_stem(term, key) for term in terms):
            out.update(ids)
    return out


def term_score(entry: dict, term: str) -> int:
    """Близость одного слова (или всей фразы) к записи — шкала в докстринге."""
    tags = [normalize(str(t)) for t in entry.get("tags") or []]
    rid = normalize(str(entry.get("id", "")))
    title = " ".join(str(entry.get("title", "").lower()).split())
    # Слова названия для сравнения форм: «транзакции,» с запятой — уже не «транзакции».
    title_words = re.findall(r"[\w-]+", title, re.UNICODE)
    if term in tags:
        return 100
    if term == rid:
        return 70
    if any(term in t for t in tags):
        return 60
    if any(same_stem(term, t) for t in tags):
        return 55
    if term in title:
        return 40
    if any(same_stem(term, w) for w in title_words):
        return 30
    if term in rid:
        return 20
    return 0


def find(query: str, section: str | None = None) -> list[dict]:
    """Записи, отсортированные по близости к запросу (при равных — по id).

    section — префикс пути («go», «database/snippets»), фильтр применяется до
    ранжирования.
    """
    query = (query or "").strip()
    phrases = forms(query)
    words = tokens(query) if phrases else []
    # Дословное совпадение фразы весит только в многословном запросе: однословный
    # запрос и есть то слово, и набавка лишь раздувала бы цифры без смысла.
    phrase_bonus = 50 if len(words) > 1 else 0
    al = aliases()
    wanted = wanted_ids(al, phrases + words)

    hits: list[tuple[int, int, str, dict]] = []
    for _, entry in index_entries():
        path = str(entry.get("path", ""))
        if section and not path.startswith(section.strip("/") + "/"):
            continue
        per_word = [term_score(entry, w) for w in words]
        exact = max([term_score(entry, p) for p in phrases] or [0])
        s = sum(per_word) + (phrase_bonus if exact else 0)
        if str(entry.get("id", "")) in wanted:
            # Алиас — явный указатель, он складывается со словами запроса, а не
            # заменяет их: «инструменты модели» сильнее, чем просто «инструмент».
            s += 80
        if phrases and s == 0:
            continue
        payload = {k: entry.get(k) for k in FIELDS}
        hits.append((s, sum(1 for v in per_word if v), str(entry.get("id", "")), payload))
    # Доля совпавших слов — второй ключ: запись, закрывающая 2 понятия из 2,
    # полезнее закрывающая 1 из 5, даже если одиночное совпадение одинаковое.
    hits.sort(key=lambda h: (-h[0], -h[1], h[2]))
    return [{**h[3], "score": h[0]} for h in hits]


if __name__ == "__main__":
    # Точка входа одна (tools/search.py): свой вывод здесь разъехался бы с ней
    # через месяц, а молчание этого файла агент читает как «записей нет».
    from search import main as cli_main  # noqa: E402

    sys.exit(cli_main())
