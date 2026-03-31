# Research: Рендер IGES в изображение

**Branch**: `002-iges-render`  
**Date**: 2026-03-30

## Decision 1: Движок рендера IGES

- **Decision**: Использовать `pythonocc-core` как основной движок чтения/рендера IGES, и `cairosvg` для генерации SVG raster-режима из промежуточного вектора при необходимости.
- **Rationale**: `pythonocc-core` даёт стабильную работу с геометрией CAD (IGES/STEP) на стороне Python и позволяет рендерить в bitmap. Это лучше соответствует backend-only сервису без GUI.
- **Alternatives considered**:
  - Рендер через внешний CLI (FreeCAD headless) — тяжелее по инфраструктуре и сложнее контроль ошибок.
  - Самописный рендер из примитивов парсера — высокий риск потерь и большая стоимость поддержки.

## Decision 2: Контракт ответа эндпоинта

- **Decision**: Возвращать бинарный файл в теле ответа с `Content-Type` (`image/png`, `image/jpeg`, `image/svg+xml`).
- **Rationale**: Это минимальный оверхед, лучший UX для клиентов и стандартный HTTP-паттерн для медиа.
- **Alternatives considered**:
  - JSON + base64 — увеличивает размер ответа и задержку.
  - URL на временный файл — требует отдельного storage/TTL и усложняет API.

## Decision 3: Метаданные и предупреждения

- **Decision**: Служебные данные передавать в HTTP-заголовках; warning о пустом/почти пустом рендере — отдельным `X-Render-Warning`.
- **Rationale**: Бинарное тело нельзя расширять JSON-полями, заголовки — естественный канал метаданных.
- **Alternatives considered**:
  - Только логи — клиент не узнает про деградацию.
  - В `Content-Disposition` — плохо машиночитаемо и не для предупреждений.

## Decision 4: Параметры PNG/JPG

- **Decision**: `width_px`, `height_px`, `dpi` с дефолтами `1600x1600` и `150 dpi`.
- **Rationale**: Покрывает preview и документные сценарии, остаётся простым для API-клиента.
- **Alternatives considered**:
  - Только max side — меньше контроля.
  - Только scale — слабая предсказуемость итоговых размеров.

## Decision 5: Поведение empty/near-empty

- **Decision**: Возвращать изображение и warning-заголовок, а не ошибку.
- **Rationale**: Не ломает pipeline, оставляет решение downstream-системе.
- **Alternatives considered**:
  - Возвращать 4xx — жёстче, но ломает существующие массовые интеграции.

## Decision 6: Тестовая стратегия

- **Decision**: Contract + integration + unit тесты обязательны для нового эндпоинта.
- **Rationale**: Конституция проекта требует защиту API-границ и интеграционных сценариев.
- **Alternatives considered**:
  - Только integration — не покрывает полноту контракта и локальную бизнес-логику классификации warning.
