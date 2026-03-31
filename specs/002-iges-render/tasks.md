# Tasks: Рендер IGES в изображение

**Input**: Design documents from `/specs/002-iges-render/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/render.md`, `quickstart.md`

**Tests**: API contract and integration tests are REQUIRED for API changes. Unit tests SHOULD be added for isolated business logic.

**Organization**: Tasks grouped by user story (US1→US3) to keep each story independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (`[US1]`, `[US2]`, `[US3]`)
- All task descriptions include exact file paths.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Подготовка структуры и зависимостей для рендера.

- [X] T001 Добавить зависимости рендера (`pythonocc-core`, `cairosvg`) в `requirements.txt`
- [X] T002 [P] Добавить конфигурацию ограничений рендера (`min/max width/height/dpi`, defaults) в `src/core/config.py`
- [X] T003 [P] Подготовить модуль рендера `src/render/__init__.py`
- [X] T004 [P] Подготовить модуль классификации предупреждений `src/render/warnings.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Базовые модели/инфраструктура, без которых user stories не стартуют.

**⚠️ CRITICAL**: Должно быть завершено до старта US1/US2/US3.

- [X] T005 Реализовать Pydantic схемы `RenderRequest`/`RenderError` и enum-поля в `src/api/schemas.py`
- [X] T006 [P] Реализовать сервисный интерфейс рендера (вход/выход bytes, format, headers metadata) в `src/render/renderer.py`
- [X] T007 [P] Реализовать базовую обработку ошибок рендера и mapping в error codes в `src/main.py`
- [X] T008 Реализовать общий helper для HTTP-заголовков `X-Render-*` в `src/api/router.py`
- [X] T009 Добавить контрактные тестовые заготовки для `/render` в `tests/contract/test_render_endpoint.py`

**Checkpoint**: Foundation ready — user story implementation can start.

---

## Phase 3: User Story 1 - Получить изображение чертежа (Priority: P1) 🎯 MVP

**Goal**: Пользователь получает PNG/JPG/SVG как бинарный ответ `image/*`.

**Independent Test**: Вызвать `POST /render` на валидном IGES и проверить MIME + открываемость файла.

### Tests for User Story 1

- [X] T010 [P] [US1] Добавить contract tests для `POST /render` success по форматам (`png`, `jpg`, `svg`) в `tests/contract/test_render_endpoint.py`
- [X] T011 [P] [US1] Добавить integration test end-to-end рендера реальной фикстуры в `tests/integration/test_render_pipeline.py`

### Implementation for User Story 1

- [X] T012 [P] [US1] Реализовать чтение/рендер IGES в PNG/JPG в `src/render/renderer.py`
- [X] T013 [P] [US1] Реализовать SVG-режим `vector` и `raster_embedded` в `src/render/renderer.py`
- [X] T014 [US1] Добавить endpoint `POST /render` с бинарным response в `src/api/router.py`
- [X] T015 [US1] Добавить заголовки `X-Render-Format` и `X-Render-Size-Bytes` в `src/api/router.py`
- [X] T016 [US1] Подключить валидацию request-параметров (`content`, `format`, `width_px`, `height_px`, `dpi`, `svg_mode`) в `src/api/schemas.py`
- [X] T017 [US1] Обновить OpenAPI описание нового эндпоинта в `src/api/router.py`

**Checkpoint**: US1 fully functional and independently testable (MVP).

---

## Phase 4: User Story 2 - Управлять параметрами рендера (Priority: P2)

**Goal**: Пользователь управляет размером/разрешением рендера и режимом SVG.

**Independent Test**: Один IGES с разными параметрами даёт ожидаемо разные размеры/характеристики результата.

### Tests for User Story 2

- [X] T018 [P] [US2] Добавить contract tests валидации диапазонов (`64..8192`, `72..600`) в `tests/contract/test_render_endpoint.py`
- [X] T019 [P] [US2] Добавить integration test сравнения результатов для разных `width_px/height_px/dpi` в `tests/integration/test_render_pipeline.py`
- [X] T020 [P] [US2] Добавить unit tests для нормализации/дефолтов render options в `tests/unit/test_renderer.py`
- [X] T040 [P] [US2] Добавить integration test различий режимов `svg_mode=vector` и `svg_mode=raster_embedded` в `tests/integration/test_render_pipeline.py`

### Implementation for User Story 2

- [X] T021 [US2] Реализовать применение defaults `1600x1600 @ 150dpi` в `src/render/renderer.py`
- [X] T022 [US2] Реализовать ветвление `svg_mode` (`vector` vs `raster_embedded`) в `src/render/renderer.py`
- [X] T023 [US2] Добавить защищённые ограничения параметров и сообщения `INVALID_RENDER_OPTIONS` в `src/api/schemas.py`
- [X] T024 [US2] Обновить quickstart примеры по параметрам в `specs/002-iges-render/quickstart.md`

**Checkpoint**: US1 + US2 independently testable.

---

## Phase 5: User Story 3 - Получать диагностические ошибки (Priority: P3)

**Goal**: Пользователь получает предсказуемые JSON-ошибки и warning header при near-empty.

**Independent Test**: Невалидные/граничные сценарии возвращают корректные `error_code`; near-empty возвращает `X-Render-Warning`.

### Tests for User Story 3

- [X] T025 [P] [US3] Добавить contract tests на `EMPTY_INPUT`, `INVALID_FORMAT`, `RENDER_ERROR`, `INTERNAL_ERROR` в `tests/contract/test_render_endpoint.py`
- [X] T026 [P] [US3] Добавить integration test near-empty case с проверкой `X-Render-Warning` в `tests/integration/test_render_pipeline.py`
- [X] T027 [P] [US3] Добавить unit tests классификации empty/near-empty в `tests/unit/test_renderer.py`

### Implementation for User Story 3

- [X] T028 [US3] Реализовать классификатор warning-кодов (`empty`, `near_empty`, `degraded`) в `src/render/warnings.py`
- [X] T029 [US3] Интегрировать warning-классификацию в pipeline рендера в `src/render/renderer.py`
- [X] T030 [US3] Добавить возврат `X-Render-Warning` в `src/api/router.py`
- [X] T031 [US3] Доработать mapping исключений рендера в `RENDER_ERROR`/`INTERNAL_ERROR` в `src/main.py`
- [X] T032 [US3] Добавить structured logging для операций рендера (`duration_ms`, `output_bytes`, `warning_code`) в `src/api/router.py`

**Checkpoint**: US1/US2/US3 all independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Финальная стабилизация, документация, проверка деплой-пути.

- [X] T033 [P] Обновить README с разделом `POST /render` в `README.md`
- [X] T034 [P] Актуализировать API-документацию render в `specs/002-iges-render/contracts/render.md`
- [X] T035 Проверить docker runtime для зависимостей рендера и обновить `Dockerfile` при необходимости
- [X] T036 [P] Добавить smoke-проверку рендера в `deploy/IGES_Parser_API.postman_collection.json`
- [X] T037 Прогнать полный тестовый набор и зафиксировать результат в `specs/002-iges-render/quickstart.md`
- [X] T038 [P] Зафиксировать регрессионный набор IGES и правила подсчета метрики успешности (>=95%) в `specs/002-iges-render/quickstart.md`
- [X] T039 [P] Добавить сценарий измерения p95 latency для `POST /render` и критерий проверки <=3s в `specs/002-iges-render/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies
- **Phase 2 (Foundational)**: depends on Phase 1; blocks all user stories
- **Phase 3 (US1)**: depends on Phase 2; MVP
- **Phase 4 (US2)**: depends on Phase 2 and integrates with US1 endpoint contract
- **Phase 5 (US3)**: depends on Phase 2 and builds diagnostics on top of US1/US2 flow
- **Phase 6 (Polish)**: depends on selected story completion (обычно US1+US2+US3)

### User Story Dependencies

- **US1 (P1)**: independent after foundation
- **US2 (P2)**: independent after foundation, reuses `/render` from US1
- **US3 (P3)**: independent after foundation, enriches error/warning behavior of `/render`

### Parallel Opportunities

- Setup: T002/T003/T004 in parallel
- Foundational: T006/T007/T009 in parallel
- US1: T010/T011 and T012/T013 in parallel
- US2: T018/T019/T020 in parallel
- US3: T025/T026/T027 in parallel
- Polish: T033/T034/T036 in parallel

---

## Parallel Example: User Story 1

```bash
# Parallel test preparation:
T010 tests/contract/test_render_endpoint.py
T011 tests/integration/test_render_pipeline.py

# Parallel renderer implementation:
T012 src/render/renderer.py (PNG/JPG)
T013 src/render/renderer.py (SVG modes, separate branch)
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1 + Phase 2.
2. Deliver Phase 3 (US1) and validate independent test criteria.
3. Release preview endpoint for early feedback.

### Incremental Delivery

1. Add US2 render options and validate parameterized output behavior.
2. Add US3 diagnostics/warnings and validate failure-mode contract.
3. Finish polish tasks and deployment verification.

### Suggested MVP Scope

- **Include**: Phase 1 + Phase 2 + Phase 3 (US1)
- **Defer**: advanced options/warnings (US2/US3) if schedule is tight

---

## Notes

- All API-changing tasks include required contract/integration tests.
- Add business-logic comments in `src/render/renderer.py` and `src/render/warnings.py` where heuristics are used.
- Keep backend-only boundary; no frontend assets.
- Quality gates: SC-002 и SC-003 проверяются через задачи T038/T039 до финального sign-off.
