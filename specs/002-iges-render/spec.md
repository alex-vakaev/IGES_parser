# Feature Specification: Рендер IGES в изображение

**Feature Branch**: `002-iges-render`  
**Created**: 2026-03-30  
**Status**: Draft  
**Input**: User description: "Нужна новая фича для приложения - рендеринг чертежа из IGES в графический формат (jpg, png, svg) и новый эндпоинт для этого."

## Clarifications

### Session 2026-03-30

- Q: В каком формате должен возвращаться результат рендера (файл/JSON base64/ссылка)? → A: Файл напрямую в теле ответа (`image/*`) + метаданные в заголовках.
- Q: Куда передавать предупреждение о пустом/почти пустом результате? → A: В отдельный HTTP-заголовок предупреждения.

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Получить изображение чертежа (Priority: P1)

Пользователь отправляет IGES-файл и получает от сервиса готовое изображение чертежа в выбранном графическом формате.

**Why this priority**: Без рендера невозможно сопоставлять текст/размеры/выноски с тем, что инженер видит на листе, и повышать качество паспорта детали.

**Independent Test**: Отправить известный IGES и визуально/программно проверить, что вернулось валидное изображение (PNG/JPG/SVG) и оно содержит видимую геометрию и текст.

**Acceptance Scenarios**:

1. **Given** валидный IGES с геометрией и аннотациями, **When** пользователь запрашивает рендер в PNG, **Then** сервис возвращает изображение в формате PNG с корректным MIME-типом.
2. **Given** валидный IGES, **When** пользователь запрашивает рендер в SVG, **Then** сервис возвращает валидный SVG, который открывается в браузере и содержит видимые элементы.

---

### User Story 2 - Управлять параметрами рендера (Priority: P2)

Пользователь задаёт параметры рендера (например, размер изображения/масштаб) и получает изображение под свои задачи (превью, печать, вставка в отчёт).

**Why this priority**: Для разных downstream сценариев (LLM, отчёты, UI-превью) нужны разные параметры и баланс качества/размера.

**Independent Test**: Запросить один и тот же IGES с двумя разными параметрами и убедиться, что результат различается ожидаемым образом (размер/детализация).

**Acceptance Scenarios**:

1. **Given** валидный IGES, **When** пользователь меняет параметр размера/разрешения, **Then** выходной файл меняет соответствующую характеристику (например, пиксельные размеры).

---

### User Story 3 - Получать диагностические ошибки (Priority: P3)

Пользователь получает понятную ошибку, если рендер невозможен (невалидный IGES, слишком большой файл, неподдерживаемый формат).

**Why this priority**: Рендер — доп. слой, ошибки должны быть объяснимыми и не ломать основной парсинг.

**Independent Test**: Отправить невалидный IGES / запросить неподдерживаемый формат и убедиться, что сервис отвечает структурированной ошибкой.

**Acceptance Scenarios**:

1. **Given** невалидный IGES, **When** пользователь вызывает рендер, **Then** сервис возвращает 4xx с понятным кодом ошибки и сообщением.

---

### Edge Cases

- Если IGES валиден, но визуально пустой или почти пустой, сервис возвращает изображение и добавляет `X-Render-Warning` с машиночитаемым кодом.
- Если рендер превышает целевое время для среднего чертежа, сервис возвращает результат, а событие фиксируется в логе с фактической длительностью для контроля SLO.
- Если запрошен неподдерживаемый формат (например, `bmp`), сервис возвращает 4xx с кодом `UNSUPPORTED_RENDER_FORMAT`.
- Если размер входа превышает лимит запроса, сервис возвращает ошибку ограничения размера и не запускает рендер.

## Technical Constraints *(mandatory)*

<!--
  ACTION REQUIRED: Capture the constitution-driven technical limits for this
  feature. Confirm stack, delivery, and operational boundaries explicitly.
-->

- **TC-001**: Feature MUST be implemented with Python and FastAPI.
- **TC-002**: Feature MUST remain backend-only and MUST NOT require a frontend.
- **TC-003**: Feature MUST define API contract, validation, and error behavior.
- **TC-004**: Feature MUST describe Docker packaging impact if it changes runtime behavior.
- **TC-005**: Feature MUST describe deployment documentation impact.
- **TC-006**: Feature MUST identify where business-logic comments are required.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements, including API behavior,
  validation, error handling, and operational requirements when relevant.
-->

### Functional Requirements

- **FR-001**: Система MUST предоставлять новый API-эндпоинт для рендера IGES в графический формат.
- **FR-002**: Эндпоинт MUST принимать IGES как текстовое содержимое (по аналогии с текущим `/parse`).
- **FR-003**: Эндпоинт MUST позволять выбрать формат результата из набора: PNG, JPG, SVG.
- **FR-004**: Система MUST возвращать результат как файл напрямую в теле HTTP-ответа (`image/png`, `image/jpeg`, `image/svg+xml`) с корректным MIME-типом.
- **FR-004a**: Система MUST возвращать метаданные рендера (как минимум формат, размер результата) в HTTP-заголовках ответа.
- **FR-004b**: Если результат рендера классифицирован как пустой или почти пустой, система MUST возвращать явный предупреждающий HTTP-заголовок (например, `X-Render-Warning`) с машинно-читаемым кодом и коротким текстом.
- **FR-005**: Система MUST применять те же базовые ограничения входа, что и парсер: обработка пустого ввода и лимит размера запроса.
- **FR-006**: Система MUST возвращать структурированную ошибку при невозможности рендера (невалидный IGES, неподдерживаемый формат, превышение лимитов).
- **FR-007**: Система MUST логировать завершение операции рендера с длительностью и размером результата.
- **FR-008**: Система MUST поддерживать параметры рендера для PNG/JPG: `width_px`, `height_px`, `dpi` с дефолтами 1600×1600 и 150 dpi.
- **FR-009**: Система MUST поддерживать два режима SVG: (1) векторный SVG и (2) SVG с embedded raster, чтобы пользователь мог выбрать компромисс “качество/надёжность vs семантика/масштабирование”.
- **FR-009a**: Система MUST обеспечивать проверяемое различие режимов SVG: в `vector` режиме документ содержит векторные элементы, в `raster_embedded` режиме документ содержит встроенное растровое представление.
- **FR-010**: Если IGES валиден, но результат рендера визуально пустой или почти пустой, система MUST вернуть изображение и явно указать предупреждение в HTTP-заголовке `X-Render-Warning` (а не падать ошибкой), чтобы downstream мог решить, что делать дальше.

### Key Entities *(include if feature involves data)*

- **RenderRequest**: входные данные IGES + параметры формата/рендера.
- **RenderResult**: графический результат + метаданные (формат, размер).
- **RenderError**: код ошибки + сообщение + диагностические детали (если доступны).

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: Пользователь может получить PNG/JPG/SVG для тестового IGES без ручных шагов конвертации и без ошибок формата.
- **SC-002**: Не менее 95% валидных IGES из набора регрессионных примеров успешно рендерятся в выбранный формат.
- **SC-003**: Время получения превью (PNG/JPG с дефолтами) для среднего чертежа не превышает 3 секунд на типовом сервере.
- **SC-004**: Ошибки рендера возвращаются в понятном виде: код + человекочитаемое сообщение, без “молчаливых” пустых результатов.
