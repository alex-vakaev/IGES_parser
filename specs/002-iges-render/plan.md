# Implementation Plan: Рендер IGES в изображение

**Branch**: `002-iges-render` | **Date**: 2026-03-30 | **Spec**: `specs/002-iges-render/spec.md`  
**Input**: Feature specification from `specs/002-iges-render/spec.md`

## Summary

Добавить новый API-эндпоинт рендера IGES в графические форматы PNG/JPG/SVG с бинарным ответом (`image/*`) и метаданными в HTTP-заголовках. Реализация сохраняет backend-only архитектуру, использует текущий стек (Python + FastAPI), добавляет диагностику пустого/почти пустого рендера через отдельный warning header и покрывается contract/integration/unit тестами.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, Pydantic v2, Uvicorn, structlog, pytest; pythonocc-core + cairosvg  
**Storage**: N/A (стейт не хранится)  
**Testing**: pytest (contract + integration + unit)  
**Target Platform**: Linux Docker container (VPS deployment)  
**Project Type**: Backend API service  
**Performance Goals**: p95 <= 3s для средних чертежей при дефолтных параметрах PNG/JPG  
**Constraints**: вход <= 10MB; бинарный ответ; backend-only; warning header для пустого рендера  
**Scale/Scope**: одиночный сервис без внешнего хранилища, до десятков рендер-запросов в минуту на один инстанс

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Uses Python and FastAPI as the primary implementation stack
- [x] Keeps scope backend-only with no frontend application introduced
- [x] Defines API contracts, validation, and error handling for affected flows
- [x] Identifies required contract, integration, and unit test coverage
- [x] Includes Docker packaging plan for the deployable service
- [x] Includes deployment documentation deliverables and validation steps
- [x] Confirms new business logic will include explanatory code comments

## Project Structure

### Documentation (this feature)

```text
specs/002-iges-render/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── render.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── api/
│   ├── router.py
│   └── schemas.py
├── core/
│   ├── config.py
│   └── middleware.py
├── parser/
│   └── ...
└── render/
    ├── __init__.py
    ├── renderer.py
    └── warnings.py

tests/
├── contract/
│   └── test_render_endpoint.py
├── integration/
│   └── test_render_pipeline.py
└── unit/
    └── test_renderer.py

deploy/
└── [optional deployment assets]

Dockerfile
docker-compose.yml
```

**Structure Decision**: Новый рендер-функционал выделяется в пакет `src/render/`, чтобы не смешивать парсинг IGES и визуализацию. API-контракт расширяется в `src/api/*`, тесты добавляются на трёх уровнях по принципам constitution.

## Phase 0: Research Plan

1. Выбрать движок рендера IGES для Python-сервиса.
2. Определить контракт бинарного ответа и заголовков метаданных.
3. Зафиксировать стратегию "empty/near-empty" результата и предупреждений.
4. Определить правила ограничения параметров `width_px/height_px/dpi`.

## Phase 1: Design & Contracts

1. Описать сущности рендера (`RenderRequest`, `RenderResult`, `RenderWarning`, `RenderError`).
2. Подготовить API-контракт нового эндпоинта (`contracts/render.md`).
3. Подготовить quickstart со сценариями PNG/JPG/SVG и разбором заголовков.
4. Обновить agent context через script.

## Phase 2: Implementation Planning (stop point for /speckit.plan)

- Подготовлены артефакты проектирования и контракты.
- Реализация и task breakdown выполняются следующим шагом (`/speckit.tasks`).

## Post-Design Constitution Re-check

- [x] Python + FastAPI unchanged
- [x] Backend-only boundary preserved
- [x] API contract + validation + errors documented
- [x] Contract/integration/unit tests explicitly planned
- [x] Docker/deployment impacts documented in quickstart and plan
- [x] Business-logic comments mandated in renderer/warning classification

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
