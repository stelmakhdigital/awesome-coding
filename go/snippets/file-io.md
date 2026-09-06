---
id: go-file-io
title: "File I/O: ReadFile, streaming, temp files"
lang: go
min_version: "1.21"
category: snippet
tags: [files, io, stdlib]
status: stable
updated: 2026-09-06
---

# File I/O

**Когда использовать** — чтение/запись файлов, стриминг больших файлов, временные файлы.
**Когда НЕ использовать** — не применимо: это базовый слой.

## Код

```go
package files

import (
	"bufio"
	"os"
	"path/filepath"
)

// 1. Целый файл в память (для файлов, которые помещаются).
func ReadAll(path string) ([]byte, error) {
	return os.ReadFile(path)
}

func WriteAll(path string, data []byte) error {
	return os.WriteFile(path, data, 0o644)
}

// 2. Стриминг: большие файлы построчно.
func ProcessLines(path string, fn func(line string) error) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()

	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024) // длиннее 64KB по умолчанию
	for scanner.Scan() {
		if err := fn(scanner.Text()); err != nil {
			return err
		}
	}
	return scanner.Err() // ОБЯЗАТЕЛЬНО: ошибка может быть в самом Scan
}

// 3. Временный файл.
func CreateTemp(dir, prefix string) (string, error) {
	tf, err := os.CreateTemp(dir, prefix+"-*")
	if err != nil {
		return "", err
	}
	name := tf.Name()
	if err := tf.Close(); err != nil {
		os.Remove(name)
		return "", err
	}
	return name, nil
}

// 4. Атомарная запись: temp + rename.
func WriteAtomic(path string, data []byte, perm os.FileMode) error {
	dir := filepath.Dir(path)
	tf, err := os.CreateTemp(dir, filepath.Base(path)+".tmp-*")
	if err != nil {
		return err
	}
	tmpName := tf.Name()
	defer os.Remove(tmpName) // если rename не случится

	if _, err := tf.Write(data); err != nil {
		tf.Close()
		return err
	}
	if err := tf.Chmod(perm); err != nil {
		tf.Close()
		return err
	}
	if err := tf.Close(); err != nil {
		return err
	}
	return os.Rename(tmpName, path)
}
```

## Pitfalls

- Всегда `defer f.Close()` сразу после успешного открытия.
- Проверяйте `f.Close()` для файлов на запись: ошибка может проявиться именно на close (flush).
- `os.ReadFile` загружает весь файл в память — для больших файлов используйте стриминг.
- `scanner.Err()` — обязательно после цикла `Scan()`.
- Атомарная запись — только внутри одного filesystem (rename между ФС не работает).

## Related

- [error-handling.md](error-handling.md)
