---
id: messaging-rules
title: "Messaging Rules (Kafka, RabbitMQ)"
lang: messaging
min_version: "4.3"
category: rule-set
tags: [rules, guardrails, kafka, rabbitmq, delivery, poison-messages]
status: stable
updated: 2026-11-24
---

# Messaging Rules — обязательные правила

## Доставка и идемпотентность

- ✅ Идемпотентный потребитель: ключ операции (`idempotency_key`) или таблица
  обработанных событий. Дубликаты — нормальны, а не авария.
- ❌ «exactly-once» как обоснование корректности: гарантия брокера — at-least-once.
  Транзакции Kafka (`acks=all` + `read_committed`) не распространяются на внешние системы.
- ✅ «Запись в БД + событие» — через outbox в той же транзакции
  ([outbox.md](snippets/outbox.md)), а не «сначала commit БД, потом publish».
- ✅ `ack` только после успешной обработки (RabbitMQ: manual ack; Kafka: commit офсетов
  после side-effect'ов).
- ❌ `auto_ack` / автокоммит офсетов при работе с БД или внешними вызовами: упал
  обработчик — сообщение потеряно.

## Отказоустойчивость

- ✅ DLQ + лимит попыток + сигнал тревоги. «Яд»-сообщение не должно блокировать партишн.
- ❌ Бесконечный retry в процессе без backoff: один битый запрос кладёт consumer.
- ✅ Backoff с jitter между попытками; после лимита — в DLQ, не «в ту же очередь».
- ✅ Graceful shutdown: перестать читать, доработать текущие, закрыть consumer
  (Kafka — оставить группу, чтобы rebalance не перебалансировал «на всегда»).
- ✅ Обработка не идемпотентной операции — только за идемпотентным ключом; повтор
  платёжки «на удачу» — это баг.

## Порядок и параллелизм

- ✅ Ключ сообщения = идентификатор сущности: порядок гарантируется в пределах партишана.
- ❌ Расчёт на глобальный порядок «всё в одной теме»: его нет.
- ✅ Одна группа консьюмеров на логического потребителя; `group_id` стабилен.
- ❌ Новый `group_id` на каждый запуск — перечитывание истории с начала.
- ✅ `MaxBytes`/prefetch (RabbitMQ QoS) под размер обработки, не «по умолчанию на 10 МБ»
  и не `prefetch=1` на высоконагруженном читателе.

## Схема сообщения

- ✅ Версия схемы в сообщении (или в реестре схем); breaking change — новая тема или
  новая версия, а не правка «на месте».
- ✅ Потребитель терпит неизвестные поля (forward compatibility); ❌ строгий
  парсер, падающий на новом поле.
- ✅ Время — UTC + явная зона в поле `occurred_at`; брокерский timestamp — метрика,
  не бизнес-время.

## Конфигурация брокера

- ✅ Для критичных тем: `acks=all` + `min.insync.replicas=2` + `retries` на продюсере.
- ✅ RabbitMQ: quorum-очереди для важного, publisher confirms, `mandatory` + обработчик
  unroutable.
- ❌ Классические mirror-очереди в новом кластере (в RabbitMQ 4.x помечены устаревающими).
- ✅ Retention осмысленный: `cleanup.policy=compact` для состояний, а не «навсегда».

## Related

- [decisions.md](decisions.md) — Kafka vs RabbitMQ vs Redis Streams
- [snippets/outbox.md](snippets/outbox.md) — атомарные «БД + событие»
- [snippets/consumer-groups.md](snippets/consumer-groups.md) — группы и идемпотентность
- [../shared/error-handling.md](../shared/error-handling.md) — ретраи и backoff
