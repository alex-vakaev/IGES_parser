# Feature Specification: IGES File Parser API

**Feature Branch**: `001-iges-parser-api`
**Created**: 2026-03-24
**Status**: Draft
**Input**: User description: "Требуется разработать приложение для парсинга IGES-файлов, содержащих инженерные чертежи деталей, сохраненные из ПО КОмпас 3D. Содержимое файлов в текстовом формате будет направляться приложению по api и в ответ нужно получить от приложения структурированный json..."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Parse IGES File and Receive Structured Drawing Data (Priority: P1)

Внешняя система (или разработчик) отправляет текстовое содержимое IGES-файла инженерного чертежа
на API и получает структурированный JSON-документ со всеми данными чертежа: метаданными,
геометрическими сущностями, размерными аннотациями и текстовыми примечаниями.

**Why this priority**: Это основная ценность всего приложения. Без этого остальное не имеет смысла.
LLM, получив этот JSON, должна иметь возможность «прочитать» чертёж и составить паспорт детали.

**Independent Test**: Тестируется отправкой текста тестового IGES-файла на POST /parse и проверкой,
что JSON-ответ содержит секции metadata, geometry, dimensions, annotations.

**Acceptance Scenarios**:

1. **Given** валидный IGES-текст чертежа из Компас 3D, **When** отправлен на эндпоинт парсинга,
   **Then** API возвращает HTTP 200 с JSON, содержащим drawing_metadata, geometry, dimensions,
   annotations и summary.
2. **Given** IGES-файл с линейными и угловыми размерами, **When** распарсен,
   **Then** JSON включает каждый размер с числовым значением, единицей и типом
   (linear / angular / radial / diameter).
3. **Given** IGES-файл с текстовыми примечаниями «Ra 3.2» и «H14»,
   **When** распарсен, **Then** JSON содержит эти строки в разделе annotations без искажений.

---

### User Story 2 - Handle Invalid or Unsupported Input (Priority: P2)

Система отправляет некорректный, пустой или не-IGES контент и получает понятный,
машиночитаемый JSON-ответ с описанием ошибки — без необработанного краша сервиса.

**Why this priority**: Без корректной обработки ошибок интеграция с downstream-системами
(LLM-пайплайн) становится хрупкой. Ясные ошибки ускоряют диагностику.

**Independent Test**: Отправить пустую строку, произвольный текст и обрезанный IGES;
убедиться, что каждый запрос возвращает структурированный JSON-error без HTTP 500.

**Acceptance Scenarios**:

1. **Given** пустое или отсутствующее тело запроса, **When** отправлено на эндпоинт,
   **Then** API возвращает HTTP 400 с JSON-ошибкой «empty input».
2. **Given** контент, не являющийся IGES-файлом, **When** отправлен,
   **Then** API возвращает HTTP 422 с описанием нарушения формата.
3. **Given** IGES-файл, превышающий допустимый размер, **When** отправлен,
   **Then** API возвращает HTTP 413 с сообщением об ограничении размера.

---

### User Story 3 - Receive Pre-Calculated Drawing Summary (Priority: P3)

Вместе с исходными данными сущностей API возвращает заранее рассчитанные сводные поля,
делающие чертёж сразу понятным: общий bounding box (габариты чертёжного поля), количество
каждого типа сущностей и нормализованные единицы измерения. Это снижает нагрузку на LLM.

**Why this priority**: Голые списки сущностей труднее интерпретирует LLM. Предрассчитанная
сводка (bounding box, счётчики, единицы) повышает точность составления паспорта детали.

**Independent Test**: Распарсить тестовый чертёж и убедиться, что JSON содержит поле summary
с bounding_box, entity_counts и units.

**Acceptance Scenarios**:

1. **Given** успешно распарсенный IGES-файл, **When** API возвращает результат,
   **Then** JSON содержит секцию summary с bounding_box (min/max X, Y), количеством
   сущностей по типам и объявленной единицей измерения.
2. **Given** чертёж с явно указанной единицей в Global-секции,
   **When** распарсен, **Then** summary.units содержит корректное значение (мм, дюйм и т.д.).

---

### Edge Cases

- Что происходит, если IGES-файл имеет корректную структуру, но не содержит геометрических
  сущностей (пустой чертёж)?
- Что происходит с типами сущностей, не поддерживаемыми парсером?
- Что происходит с кириллическими строками в текстовых примечаниях (Компас 3D — ГОСТ)?
- Что происходит при обрезанной или повреждённой секции Parameter Data?
- Что происходит при файле, превышающем лимит по размеру или по времени обработки?

## Technical Constraints *(mandatory)*

- **TC-001**: Feature MUST be implemented with Python and FastAPI.
- **TC-002**: Feature MUST remain backend-only and MUST NOT require a frontend.
- **TC-003**: Feature MUST define API contract: эндпоинт, схема запроса/ответа,
  HTTP-статусы, формат ошибок.
- **TC-004**: Feature MUST be packaged as a Docker container with documented startup
  and configuration.
- **TC-005**: Feature MUST include deployment instructions covering environment variables,
  build steps, and API verification.
- **TC-006**: IGES-парсинг, извлечение сущностей и нормализация вывода MUST include
  comments explaining business purpose.
- **TC-007**: Сервис MUST писать структурированные JSON-логи в stdout. Каждая обработка
  запроса MUST фиксировать: HTTP-статус, размер входного контента, время обработки (мс),
  все ошибки с типом и сообщением.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept IGES file content as UTF-8 or ASCII text via a single
  HTTP POST endpoint. Request body MUST use `application/json` with the field `content`
  (string, required). Example: `{"content": "<iges text>"}`.
  Raw IGES-параметры включаются в ответ всегда; поле `options` отсутствует.
- **FR-002**: System MUST parse all five IGES sections: Start, Global, Directory Entry,
  Parameter Data, Terminate.
- **FR-003**: System MUST extract drawing metadata from the Global section: единица
  измерения, масштаб, автор, организация, дата создания, обозначение/наименование
  чертежа, версия IGES.
- **FR-004**: System MUST extract geometric entities — lines (Type 110), circular arcs
  (Type 100), conic arcs (Type 104), composite curves (Type 102), copious data /
  witness lines (Type 106), rational B-spline curves (Type 126), points (Type 116),
  sectioned areas (Type 230) — с координатами и атрибутами (слой, цвет, толщина
  линии). Каждая сущность MUST также включать поле `raw_parameters` с исходными
  параметрами из секции Parameter Data IGES-файла (максимально полный вывод).
- **FR-005**: System MUST extract dimension annotation entities — linear (Type 216),
  angular (Type 202), radius (Type 222), diameter (Type 206), ordinate (Type 218) —
  с числовым значением, единицей, координатами привязки и полем `raw_parameters`
  с исходными параметрами из P-секции.
- **FR-006**: System MUST extract text annotation entities — general notes (Type 212)
  и general labels (Type 210) — сохраняя полное текстовое содержимое и позицию.
- **FR-007**: System MUST extract leader/arrow entities (Type 214), связанных с
  размерами и примечаниями.
- **FR-008**: System MUST return all extracted data as a single structured JSON document
  following a documented, stable schema.
- **FR-009**: System MUST calculate and include a drawing summary: bounding box
  (min/max X и Y по всей геометрии), количество сущностей по типам, объявленная
  единица измерения.
- **FR-010**: System MUST return structured error responses for invalid input, format
  violations, and oversized requests. Error response schema:
  `{"error_code": "<SCREAMING_SNAKE_CASE>", "message": "<human-readable>", "details": {}}`.
  Defined error codes: `EMPTY_INPUT`, `INVALID_FORMAT`, `SIZE_EXCEEDED`, `PARSE_ERROR`,
  `INTERNAL_ERROR`.
- **FR-011**: System MUST correctly handle Cyrillic text in General Note и General Label
  entities without encoding errors (распространено в чертежах Компас 3D по ГОСТ).
- **FR-012**: Unsupported IGES entity types MUST be recorded in the response under
  "unsupported_entities" list (с их type number), а не вызывать ошибку парсинга.

### Key Entities

- **ParseRequest**: Текстовое содержимое IGES-файла (строка) в поле `content`.
  Поле `options` не нужно — raw-параметры включаются в ответ всегда.
- **ParseResponse**: Корневой объект ответа: drawing_metadata, geometry, dimensions,
  annotations, summary, unsupported_entities.
- **DrawingMetadata**: Автор, организация, дата создания, обозначение чертежа, единица
  измерения, масштаб, версия IGES, стандарт оформления (ГОСТ / ISO).
- **GeometricEntity**: Номер типа сущности, читаемое имя типа, слой, цвет, толщина
  линии, координатные данные (зависят от типа).
- **DimensionAnnotation**: Тип размера (linear / angular / radial / diameter / ordinate),
  числовое значение, единица, текстовое представление «как на чертеже»,
  координаты стрелок.
- **TextAnnotation**: Полный текст, позиция (X, Y), высота символов.
- **DrawingSummary**: Bounding box (min_x, min_y, max_x, max_y), счётчики сущностей
  по типу, объявленная единица измерения, общее число сущностей.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: При валидном IGES-файле из Компас 3D API возвращает полный JSON
  не более чем за 5 секунд для файлов до 5 МБ при нагрузке до 5 одновременных запросов.
- **SC-002**: JSON захватывает 100% размерных аннотаций тестового эталонного чертежа
  с корректными числовыми значениями и типами.
- **SC-003**: JSON захватывает 100% текстовых примечаний, включая кириллические,
  без ошибок кодировки.
- **SC-004**: LLM, получившая JSON, способна без обращения к исходному IGES-файлу
  определить как минимум: габаритные размеры детали, все аннотированные размеры
  и текстовые примечания (допуски, шероховатость).
- **SC-005**: Все некорректные или повреждённые входные данные возвращают
  структурированный JSON-error; ни один входной файл не вызывает HTTP 500.
- **SC-006**: Разработчик может развернуть сервис локально за 30 минут, следуя
  только документированным шагам, без дополнительных консультаций.

## Clarifications

### Session 2026-03-24

- Q: Как именно IGES-текст передаётся в теле HTTP-запроса? → A: `application/json` с полем `content` (строка). Поле `options` не нужно.
- Q: Что включать в секцию `geometry` — только аннотации, примитивы без raw-данных, или всё? → A: Все геометрические примитивы с координатами и raw IGES-параметрами всегда (максимально полный вывод).
- Q: Какой уровень логирования требуется от сервиса? → A: Структурированные JSON-логи в stdout: каждый запрос (статус, размер входа, время обработки) + все ошибки.
- Q: Ожидаемая пиковая нагрузка на сервис? → A: До 5 одновременных запросов; очереди и горизонтальное масштабирование вне скоупа v1.
- Q: Какой формат JSON-ошибки использовать? → A: `{"error_code": "INVALID_FORMAT", "message": "...", "details": {...}}`.

## Assumptions

- IGES-файлы экспортируются из Компас 3D по стандарту ГОСТ; парсер приоритизирует
  2D-сущности чертежа над 3D-поверхностями и телами.
- Файл передаётся как UTF-8 или ASCII текстовая строка в теле HTTP-запроса;
  бинарные или сжатые варианты IGES — вне скоупа.
- Хранение файлов не требуется; API stateless, обрабатывает каждый запрос независимо.
- Максимальный размер принимаемого файла — 10 МБ; бо́льшие файлы вне скоупа v1.
- API не интерпретирует семантику чертежа (например, не распознаёт «это отверстие»);
  интерпретация — задача LLM.
- Шероховатость, допуски и марка материала встречаются в виде текста в General Note
  (Type 212); парсер извлекает их как raw-текст, без семантического разбора.
- Аутентификация и rate limiting — вне скоупа v1; добавляются отдельной фичей.
