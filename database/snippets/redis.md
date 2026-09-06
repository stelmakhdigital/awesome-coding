---
id: database-redis
title: "Redis: кэширование, структуры данных, TTL"
lang: database
min_version: "8"
category: snippet
tags: [redis, caching, ttl, data-structures, streams]
status: stable
updated: 2026-09-06
---

# Redis: кэш и структуры данных

**Когда использовать** — кэш read-heavy, сессии, счётчики, лёгкие очереди, rate limiting.
**Когда НЕ использовать** — как единственное хранилище критичных данных (Redis — не источник истины).

## Cache-aside (базовый паттерн)

```go
// Чтение: Redis -> БД; запись: БД -> инвалидация Redis.
func GetUser(ctx context.Context, id string) (User, error) {
    key := "user:" + id
    if b, err := rdb.Get(ctx, key).Bytes(); err == nil {
        var u User
        if err := json.Unmarshal(b, &u); err == nil {
            return u, nil
        }
    }
    u, err := dbUser(ctx, id) // БД
    if err != nil {
        return User{}, err
    }
    b, _ := json.Marshal(u)
    rdb.Set(ctx, key, b, 10*time.Minute) // TTL обязателен
    return u, nil
}

func UpdateUser(ctx context.Context, u User) error {
    if err := dbSaveUser(ctx, u); err != nil {
        return err
    }
    rdb.Del(ctx, "user:"+u.ID) // инвалидация после записи
    return nil
}
```

## Правила кэша

1. **TTL — всегда** (5–30 мин): без TTL — устаревшие данные навсегда.
2. **Инвалидация после записи** (не до): запись в БД → `DEL`.
3. **Ключи — именованные пространства**: `user:42`, `order:idx:status:unpaid`.
4. **Не кэшируйте «всё»**: только read-heavy + дорогие запросы.
5. **Cache stampede** (пробой при истечении): на короткий срок — mutex/lock на пересчёт
   (`SET key lock NX EX 5`) или stale-while-revalidate.
6. **Размер значения**: < 10KB; большие — сжать или не кэшировать.

## Структуры данных

| Структура | Команды | Применение |
|---|---|---|
| String | `GET/SET/INCR` | кэш, счётчики, флаги |
| Hash | `HSET/HGETALL` | объект по полям (пользователь) |
| List | `LPUSH/BRPOP` | простая очередь (FIFO) |
| Set | `SADD/SMEMBERS` | уникальные множества, теги |
| Sorted Set | `ZADD/ZRANGEBYSCORE` | топы, очереди по приоритету, rate limit |
| Stream | `XADD/XREADGROUP` | надёжная очередь с группами потребителей |

```go
// Rate limit: sliding window через sorted set.
// key = "rl:user:42"; score = timestamp; member = уникальный id запроса
rdb.ZAdd(ctx, key, redis.Z{Score: now, Member: reqID})
rdb.ZRemRangeByScore(ctx, key, "-inf", fmt.Sprint(now-window))
count, _ := rdb.ZCard(ctx, key).Result()
if count > limit { /* 429 */ }
rdb.Expire(ctx, key, window+time.Minute)
```

## Ошибки

- ❌ «Данные живут только в Redis» — потеря при сбое (RDB/AOF не гарантия).
- ❌ `KEYS *` в production — `SCAN`.
- ❌ Горячий ключ (один key на весь трафик) — шардирование (`user:{shard}:42`).
- ❌ Блокирующие операции в критичном пути (`SMEMBERS` на большом сете).
- ✅ Мониторинг: `used_memory`, `evicted_keys`, `rejected_connections`, hit-rate кэша.

## Related

- [decisions.md — кэширование](../decisions.md)
- [messaging/](../../messaging/) — когда нужен настоящий брокер
