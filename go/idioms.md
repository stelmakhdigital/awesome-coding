---
id: go-idioms
title: Go Idioms
lang: go
min_version: "1.21"
category: idioms
tags: [idioms, style, patterns, stdlib]
status: stable
updated: 2026-09-06
---

# Go — Idioms

Короткие идиомы, которые отличают идиоматичный Go.

## Defer для cleanup

```go
f, err := os.Open(path)
if err != nil {
    return err
}
defer f.Close() // сразу после успешного открытия
```

## Single return

Одна точка возврата в конце — читаемее, чем return в каждом if (кроме guard clauses).

## Интерфейс из одного метода

```go
type Gopher interface{ Eat() }
```

Интерфейсы определяет потребитель (consumer-defined), а не производитель. Не создавайте интерфейс «на вырост».

## Ошибки — значения

```go
var ErrNotFound = errors.New("not found") // sentinel
// сравнение: errors.Is(err, ErrNotFound)
```

## Type assertion с comma-ok

```go
if e, ok := err.(*ValidationError); ok {
    log.Printf("field %s", e.Field)
}
```

## any вместо interface{}

```go
func Log(v any) { ... } // Go 1.18+
```

## Variadic + функциональные опции

См. [patterns/functional-options](patterns/functional-options.md).

## Table-driven тесты

См. [snippets/testing](snippets/testing.md).

## init() — осторожно

`init()` — только для лёгкой инициализации пакетов (регистрация драйверов и т.п.). Любая логика — в явную функцию `New()`.

## iota для enum-констант

```go
type Level int

const (
    LevelDebug Level = iota
    LevelInfo
    LevelError
)
```

## Пустой интерфейс — any

Пустой `interface{}` и `any` — одно и то же; пишите `any`.

## Не копируйте, передавайте срезы

Срез — дескриптор (header + указатель на backing array). Передача по значению не копирует данные, но и не изолирует: изменения элементов видны обоим.
