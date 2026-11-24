---
id: react-feature-structure
title: "React: структура проекта по фичам"
lang: react
min_version: "19.3"
category: pattern
tags: [structure, feature-sliced, folders, boundaries, imports, scaling]
status: stable
updated: 2026-11-25
---

# Структура проекта по фичам

**Когда использовать** — во фронтенде больше 10 экранов, и правка одной фичи трогает файлы в четырёх папках (`components/`, `hooks/`, `api/`, `store/`). Также — когда в проект приходят люди или агенты и первый вопрос «где это?» стоит дороже, чем длина пути.
**Когда НЕ использовать** — прототип на 5 файлов: слои и правила импорта окупятся после первого месяца роста, до этого это ceremony.

## Форма

```text
src/
  app/                    # сборка приложения: роутер, провайдеры, layout
    App.tsx
    router.tsx
    providers.tsx
  shared/                 # то, что не принадлежит ни одной фиче
    ui/                   # Button, Panel, Field — без бизнес-правил
    api/                  # fetch-клиент, типы ответов, разбор ошибок
    hooks/                # useLocalStorage, useMediaQuery
    lib/                  # чистые функции: формат, парсер, даты
  features/
    interview/
      api.ts              # вызовы + разбор ответа (zod) — единственная точка выхода в сеть
      model.ts            # редьюсер стадий, типы
      hooks.ts            # useInterview — то, что видят соседи
      InterviewPanel.tsx
      StageBar.tsx
      api.test.ts
      model.test.ts
      index.ts            # публичный фасад: export { useInterview, InterviewPanel }
    whiteboard/
      ...
  widgets/                # крупные составные куски из нескольких фич
    session-header/
      SessionHeader.tsx
      SessionHeader.test.tsx
  main.tsx
```

## Правила, без которых структура не работает

- Импорт чужой фичи — только через её `index.ts`. `import { stage } from "@/features/interview/model"` — это проход в чужие внутренности, и через месяц он держит пол-проекта.
- Направление зависимостей: `app → widgets → features → shared`. `shared` не знает о фичах, `features` не знают друг о друге. Исключение — события и колбэки, переданные сверху.
- Тест рядом с файлом (`model.test.ts`), а не в отдельном дереве `__tests__`: правка и её проверка видны в одном месте, а «забытый тест» заметен глазами, а не в диффе.
- `api.ts` фичи — единственное место, где эта фича ходит в сеть. Иначе контракт API выясняется по 12 местам вызова.
- Общие компоненты живут в `shared/ui` только после второго потребителя. Первый — локально в фиче.
- Алиас `@/` на `src` — плюс к читаемости и никакой магии: `resolve.tsconfigPaths: true` в Vite 8 подхватывает `tsconfig.paths` ([../snippets/vite.md](../snippets/vite.md)).

## Когда фича вырастает

Признаки, что пора делить:

| Признак | Что делать |
|---|---|
| `index.ts` экспортирует 15 вещей | две фичи: экспорт — это контракт, он разросся |
| `hooks.ts` на 400 строк | разбить по сущностям (`useInterview`, `useInterviewTimer`) и оставить фасад |
| Фича импортирует другую фичу | поднять общее в `shared` или передавать сверху пропсом/колбэком |
| Фича знает про роуты и стор целиком | она не фича, а экран: переезжает в `app` или `widgets` |
| Правка затрагивает 6 файлов в 3 папках | неверная граница: делить по сущности, а не по типу файла |

## Related

- [../architecture/patterns/layered.md](../../architecture/patterns/layered.md) — слои и направление зависимостей на бэкенде
- [../architecture/ddd/strategic/bounded-context.md](../../architecture/ddd/strategic/bounded-context.md) — граница фичи как граница контекста
- [../shared/documentation.md](../../shared/documentation.md) — `PROJECT_MEMORY.md`: чем дополнять структуру, когда файлов становится больше
