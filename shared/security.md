---
id: shared-security
title: "Shared: Security (кросс-языковые принципы)"
lang: shared
min_version: null
category: concept
tags: [security, owasp, secrets, injection, tls]
status: stable
updated: 2026-09-07
---

# Security — принципы

**Когда использовать** — любой код, работающий с внешним вводом, секретами, сетью, данными.
**Когда НЕ использовать** — n/a: базовая запись.

## Принципы (OWASP-ядро)

1. **Не верьте вводу**: валидация на границе (схема/тип), санитизация — не замена.
2. **Параметризованные запросы** — всегда. Конкатенация SQL/команд — только с проверенными константами.
3. **Секреты — не в коде/репо**: env/secret manager; `.env` — в `.gitignore`.
4. **Шифрование**: TLS для транспорта; хеширование паролей — `argon2`/`bcrypt` (не MD5/SHA1).
5. **Минимальные привилегии**: сервис — с минимальными правами (DB-юзер без DDL, контейнер non-root).
6. **Зависимости**: аудит (CVE), минимальный набор, закреплённые версии.

## ✅ / ❌

- ✅ `db.Query("SELECT ... WHERE id = $1", id)` — параметризация
- ❌ `db.Query("SELECT ... WHERE id = " + id)` — SQL injection
- ✅ Секрет из env/secret manager, валидация на старте
- ❌ Токен в коде/коммитах/логах
- ✅ `argon2id`/`bcrypt` для паролей
- ❌ `md5`/`sha1` для паролей; «соль» — per-user random
- ✅ HTTPS-only; `Secure`/`HttpOnly`/`SameSite` для cookie
- ❌ Печать PII/секретов в логах
- ✅ Ограничение размера тела/количества запросов (rate limit)
- ❌ Доверие заголовкам `X-Forwarded-*` без проверки источника
- ❌ Десериализация недоверенных данных: `pickle`/`yaml.load`/Java-десериализация/XXE — вектор RCE
- ❌ `curl | bash` — скачать, проверить хэш/подпись, потом выполнять
- ❌ Секреты в клиентском коде (web-бандл, APK/IPA) — клиент публичный, реверсится
- ✅ Supply chain: lock-файлы в репо, минимальный набор зависимостей, CVE-аудит
  (`npm audit`/`pip-audit`/Dependabot), checksums при загрузке артефактов

## По языкам

| Язык | Ключевые инструменты |
|---|---|
| Go | `database/sql` (параметры), `crypto/sha256`, `golang.org/x/crypto/bcrypt` |
| C# | `Microsoft.Data.SqlClient` (параметры), `System.Security.Cryptography` |
| Python | `psycopg` (параметры), `bcrypt`, `secrets` (не `random`) |
| TS/JS | `pg`/`mysql2` (параметры), `crypto` (node), `argon2` |
| Kotlin | JDBC/Exposed (параметры), `bcrypt` |
| C | prepared statements (libpq), `openssl` |
| Bash | кавычки всегда: `"$var"`, не `eval` с внешним вводом |

## Related

- [configuration.md](configuration.md) — секреты в конфигурации
- [observability.md](observability.md) — что НЕ писать в логи
