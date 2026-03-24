# Tasks: IGES File Parser API

**Input**: Design documents from `specs/001-iges-parser-api/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Можно выполнять параллельно (разные файлы, нет незавершённых зависимостей)
- **[Story]**: US1, US2, US3 — к какому пользовательскому сценарию относится задача
- Точные пути к файлам указаны в каждой задаче

## Path Conventions

- Исходный код: `src/` в корне репозитория
- Тесты: `tests/` в корне репозитория
- Docker-файлы: корень репозитория
- Тестовые фикстуры: `tests/fixtures/`

---

## Phase 1: Setup

**Purpose**: Инициализация проекта, зависимости, Docker-сборка

- [X] T001 Создать структуру директорий: `src/api/`, `src/parser/entities/`, `src/models/`, `src/core/`, `tests/contract/`, `tests/integration/`, `tests/unit/`, `tests/fixtures/`, `deploy/`
- [X] T002 Создать `requirements.txt` с зависимостями: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `structlog`, `pytest`, `pytest-asyncio`, `httpx`
- [X] T003 [P] Создать `pyproject.toml` с настройками ruff (линтер) и pytest (asyncio_mode = auto)
- [X] T004 [P] Создать `Dockerfile` (multi-stage: builder + runtime, Python 3.11-slim, WORKDIR /app, CMD uvicorn)
- [X] T005 [P] Создать `docker-compose.yml` с сервисом `iges-parser` (build, ports: 8000, env_file: .env)
- [X] T006 [P] Создать `.env.example` со всеми переменными окружения: `APP_HOST`, `APP_PORT`, `APP_WORKERS`, `MAX_CONTENT_BYTES`, `LOG_LEVEL`, `LOG_FORMAT`

---

## Phase 2: Foundational

**Purpose**: Core-инфраструктура, блокирующая все пользовательские сценарии

**⚠️ CRITICAL**: Ни один пользовательский сценарий не может быть начат до завершения этой фазы

- [X] T007 Создать `src/core/config.py` — pydantic-settings класс `Settings`, читающий переменные окружения; дефолты совпадают с `.env.example`
- [X] T008 [P] Создать `src/core/logging.py` — настройка structlog: JSON-рендерер при `LOG_FORMAT=json`, ConsoleRenderer при `pretty`; функция `get_logger()`
- [X] T009 [P] Создать `src/core/middleware.py` — `ContentSizeLimitMiddleware`: проверяет `Content-Length` заголовок, при превышении `MAX_CONTENT_BYTES` возвращает HTTP 413 с телом `{"error_code": "SIZE_EXCEEDED", ...}`
- [X] T010 Создать `src/main.py` — FastAPI app: подключить middleware (T009), роутер из `src/api/router.py`, настроить логирование (T008); импортировать конфиг (T007)
- [X] T011 [P] Создать `src/api/__init__.py`, `src/parser/__init__.py`, `src/parser/entities/__init__.py`, `src/models/__init__.py`, `src/core/__init__.py` (пустые файлы пакетов); создать `tests/conftest.py` с фикстурой `async_client` (httpx.AsyncClient + ASGITransport) для всех contract и integration тестов
- [X] T012 Реализовать `GET /health` в `src/api/router.py` — возвращает `{"status": "ok"}` (HTTP 200); добавить JSON-лог старта сервиса в `src/main.py`

**Checkpoint**: После этой фазы `docker compose up --build` поднимает сервис, `/health` отвечает `{"status": "ok"}`

---

## Phase 3: US1 — Parse IGES File → Structured JSON (Priority: P1) 🎯 MVP

**Goal**: Принять IGES-текст, вернуть полный структурированный JSON с метаданными, геометрией, размерами, аннотациями и сводкой

**Independent Test**: `POST /parse` с содержимым тестового `simple_drawing.igs` → HTTP 200, JSON содержит поля `drawing_metadata`, `geometry`, `dimensions`, `annotations`, `summary`

### Тесты для US1 (писать ДО реализации — должны падать) ⚠️

- [X] T013 [P] [US1] Contract-тест схемы ответа `POST /parse` в `tests/contract/test_parse_endpoint.py`: HTTP 200, все поля ParseResponse присутствуют, типы корректны
- [X] T014 [P] [US1] Integration-тест полного цикла парсинга в `tests/integration/test_full_parse.py`: отправить `tests/fixtures/simple_drawing.igs`, проверить непустые списки geometry, dimensions, annotations

### Реализация US1

- [X] T015 [P] [US1] Создать все Pydantic-схемы в `src/api/schemas.py`: `ParseRequest`, `ParseResponse`, `DrawingMetadata`, `GeometricEntity`, `DimensionAnnotation`, `TextAnnotation`, `BoundingBox`, `DrawingSummary`, `UnsupportedEntityRecord`, `ErrorResponse`
- [X] T016 [P] [US1] Создать внутренние dataclass-модели в `src/models/internal.py`: `IgesSection`, `EntityHeader`, `RawEntity` — промежуточные структуры между парсером и API-схемами
- [X] T017 [P] [US1] Реализовать `IgesReader` в `src/parser/iges_reader.py`: метод `split_sections(text: str) -> IgesSections` разбивает текст по символу позиции 73 каждой строки (S/G/D/P/T); комментарии с бизнес-логикой обязательны
- [X] T018 [P] [US1] Реализовать `GlobalParser` в `src/parser/global_parser.py`: метод `parse(g_lines: list[str]) -> DrawingMetadata`; разбирает comma-delimited поля P1-P26 по стандарту IGES 5.3, Hollerith-строки декодирует как Unicode; комментарии обязательны
- [X] T019 [P] [US1] Реализовать `DirectoryParser` в `src/parser/directory_parser.py`: метод `parse(d_lines: list[str]) -> dict[int, EntityHeader]`; каждая DE-запись занимает 2 строки по 80 символов с фиксированными полями 8 символов; комментарии обязательны
- [X] T020 [P] [US1] Реализовать парсеры геометрических сущностей в `src/parser/entities/geometry.py`: функции `parse_type_100`, `parse_type_102`, `parse_type_104`, `parse_type_106`, `parse_type_110`, `parse_type_116`, `parse_type_126`, `parse_type_230`; для каждого типа — комментарий с объяснением бизнес-значения (что это за объект на чертеже)
- [X] T021 [P] [US1] Реализовать парсеры размерных сущностей в `src/parser/entities/dimensions.py`: функции `parse_type_202`, `parse_type_206`, `parse_type_216`, `parse_type_218`, `parse_type_222`; для каждого — комментарий о том, что за размер это обозначает
- [X] T022 [P] [US1] Реализовать парсеры аннотационных сущностей в `src/parser/entities/annotations.py`: функции `parse_type_210`, `parse_type_212`, `parse_type_214`; Type 212 (General Note) содержит шероховатость/допуски — комментарий обязателен
- [X] T023 [US1] Реализовать `EntityDispatcher` в `src/parser/entity_dispatcher.py`: метод `dispatch(p_lines, directory) -> tuple[list[GeometricEntity], list[DimensionAnnotation], list[TextAnnotation], list[UnsupportedEntityRecord]]`; маршрутизирует по entity_type из directory; неизвестные типы → unsupported list; комментарии обязательны (зависит от T020, T021, T022); **также реализовать `compute_summary(geometry, dimensions, annotations, metadata) -> DrawingSummary`** в том же файле: вычисляет bounding box по coordinates геометрии (None если geometry пуст), строит entity_counts по entity_name, берёт units из metadata; комментарии обязательны
- [X] T024 [US1] Реализовать `POST /parse` в `src/api/router.py`: оркестрирует IgesReader → GlobalParser → DirectoryParser → EntityDispatcher, формирует ParseResponse; JSON-лог запроса (статус, размер, время); комментарии обязательны (зависит от T015, T017, T018, T019, T023)
- [X] T025 [P] [US1] Добавить `tests/fixtures/simple_drawing.igs` — минимальный валидный IGES-файл с одной линией и одним размером (создать вручную по стандарту или скопировать из открытых источников)
- [X] T026 [P] [US1] Unit-тесты для `IgesReader` в `tests/unit/test_iges_reader.py`: тест разбивки на 5 секций, тест обработки файла без Terminate-секции
- [X] T027 [P] [US1] Unit-тесты для `GlobalParser` в `tests/unit/test_global_parser.py`: тест извлечения unit, author, drawing_title; тест с кириллицей в Hollerith-поле
- [X] T028 [P] [US1] Unit-тесты для парсеров сущностей в `tests/unit/test_entity_parsers.py`: по одному тест-кейсу на каждый из 16 поддерживаемых типов сущностей

**Checkpoint**: `POST /parse` с `simple_drawing.igs` возвращает HTTP 200 с корректным JSON; все тесты фазы зелёные

---

## Phase 4: US2 — Handle Invalid or Unsupported Input (Priority: P2)

**Goal**: Все некорректные входные данные возвращают структурированный ErrorResponse; HTTP 500 недостижим

**Independent Test**: Отправить пустую строку, произвольный текст, обрезанный IGES → каждый возвращает JSON `{"error_code": "...", "message": "...", "details": {...}}` и код 400/422/413

### Тесты для US2 (писать ДО реализации — должны падать) ⚠️

- [X] T029 [P] [US2] Contract-тесты всех ошибочных ответов в `tests/contract/test_parse_endpoint.py`: пустой content → 400 `EMPTY_INPUT`; не-IGES текст → 422 `INVALID_FORMAT`; контент > лимита → 413 `SIZE_EXCEEDED`; валидный IGES с повреждённой P-секцией → 422 `PARSE_ERROR`

### Реализация US2

- [X] T030 [US2] Добавить валидацию `content` на пустоту в `src/api/router.py` перед вызовом парсера → HTTP 400 `EMPTY_INPUT`
- [X] T031 [US2] Добавить определение формата IGES в `src/parser/iges_reader.py`: если Start-секция не найдена в первых 100 строках → поднять `IgesFormatError`; роутер перехватывает → HTTP 422 `INVALID_FORMAT`
- [X] T032 [US2] Добавить обработку `ParseError` в `EntityDispatcher` при повреждённых параметрах сущности: логировать предупреждение, пропускать сущность (не ронять запрос); если повреждена > 50% сущностей — поднять `ParseError` → HTTP 422 `PARSE_ERROR`
- [X] T033 [P] [US2] Добавить глобальный exception handler в `src/main.py`: любое необработанное исключение → HTTP 500 `INTERNAL_ERROR`; стек трейс пишется в лог, клиенту не отдаётся
- [X] T034 [P] [US2] Добавить `tests/fixtures/invalid.txt` и `tests/fixtures/truncated.igs` для тестов ошибок

**Checkpoint**: Ни один тестовый некорректный запрос не вызывает HTTP 500; все contract-тесты ошибок зелёные

---

## Phase 5: US3 — Validate Drawing Summary & Cyrillic (Priority: P3)

**Goal**: Верифицировать корректность summary (bounding box, счётчики, единицы) на реальных и edge-case чертежах, включая файлы Компас 3D с кириллицей. Реализация summary уже выполнена в T023 (Phase 3).

**Independent Test**: Распарсить `kompas_sample.igs` и убедиться, что `summary.bounding_box` не None, `summary.entity_counts` не пустой, `summary.units` совпадает с `drawing_metadata.unit`; все кириллические `annotations[*].content` без искажений

### Тесты для US3 (писать ДО — проверяют поведение edge-cases) ⚠️

- [X] T035 [P] [US3] Unit-тесты `compute_summary` в `tests/unit/test_entity_parsers.py`: тест с набором линий → корректные min/max X и Y; тест с **пустой геометрией** → `bounding_box is None`; тест entity_counts по типам
- [X] T036 [P] [US3] Integration-тест Cyrillic в `tests/integration/test_full_parse.py`: отправить `tests/fixtures/kompas_sample.igs` → `annotations[*].content` содержит корректный Unicode без `?` и кракозябр; `summary.units` == значение из metadata

### Реализация US3

- [X] T037 [US3] Добавить `tests/fixtures/kompas_sample.igs` — IGES-файл из Компас 3D с кириллическими примечаниями; если реального файла нет — создать программный генератор тестовой фикстуры в `tests/fixtures/generate_fixtures.py` с заданными параметрами
- [X] T038 [US3] Дополнить `tests/fixtures/simple_drawing.igs`: убедиться, что фикстура содержит хотя бы один размер каждого типа (linear, angular, radius) и одно General Note с текстом «Ra 3.2» для проверки annotations-pipeline

**Checkpoint**: `summary` корректно заполняется для всех тестовых файлов; кириллица отображается без ошибок; edge-case пустой геометрии возвращает `bounding_box: null`

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Финализация Docker, проверка деплоя, комментарии, security

- [X] T040 [P] Проверить все функции парсера на наличие business-logic комментариев (`src/parser/**/*.py`): каждая функция должна иметь docstring + inline-комментарии там, где логика неочевидна (конституция, Принцип III)
- [X] T041 Финальная проверка Docker: `docker compose up --build` → `/health` → `POST /parse` с реальным IGES-файлом → JSON-лог в stdout; задокументировать результат в `specs/001-iges-parser-api/quickstart.md`
- [X] T042 [P] Добавить `GET /docs` и `GET /openapi.json` упоминание в `specs/001-iges-parser-api/quickstart.md` (FastAPI генерирует автоматически, нужно только убедиться что работают)
- [X] T043 [P] Security: убедиться что `INTERNAL_ERROR` не раскрывает стек трейс клиенту (проверить handler из T033); убедиться что лог не пишет содержимое IGES-файла целиком (только размер)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: Нет зависимостей — можно начинать немедленно
- **Phase 2 (Foundational)**: Зависит от Phase 1 — блокирует все пользовательские сценарии
- **Phase 3 (US1)**: Зависит от Phase 2; MVP — только эта фаза достаточна для демонстрации
- **Phase 4 (US2)**: Зависит от Phase 2; можно вести параллельно с US1 после T012
- **Phase 5 (US3)**: Зависит от Phase 3 (нужны GeometricEntity с координатами)
- **Phase N (Polish)**: Зависит от всех пользовательских сценариев

### Within US1 — Execution Order

```
T013, T014 (тесты — пишем первыми, должны падать)
    ↓
T015, T016, T017, T018, T019, T020, T021, T022 (параллельно — разные файлы)
    ↓
T023 (EntityDispatcher — зависит от T020, T021, T022)
    ↓
T024 (router POST /parse — зависит от T015, T017, T018, T019, T023)
    ↓
T025, T026, T027, T028 (фикстуры + unit-тесты — параллельно)
```

### Within US2 — Execution Order

```
T029 (тесты — пишем первыми)
    ↓
T030, T031, T032, T033, T034 (реализация — T030/T031/T032/T033/T034 параллельно)
```

### Within US3 — Execution Order

```
T035, T036 (тесты — edge-cases и Cyrillic)
    ↓
T037 (kompas_sample.igs fixture) + T038 (дополнить simple_drawing.igs) — параллельно
```
*Примечание: compute_summary реализован в T023 (Phase 3); T039 удалён как избыточный*

### Parallel Opportunities

- **Phase 1**: T003, T004, T005, T006 — все параллельно после T001, T002
- **Phase 2**: T008, T009 — параллельно после T007
- **Phase 3 impl**: T015–T022 — все параллельно (разные файлы)
- **Phase 3 tests**: T026, T027, T028 — параллельно

---

## Parallel Example: US1

```bash
# Запустить тесты (должны падать):
Task: "T013 — contract-тест POST /parse в tests/contract/test_parse_endpoint.py"
Task: "T014 — integration-тест в tests/integration/test_full_parse.py"

# Запустить реализацию парсеров параллельно:
Task: "T017 — IgesReader в src/parser/iges_reader.py"
Task: "T018 — GlobalParser в src/parser/global_parser.py"
Task: "T019 — DirectoryParser в src/parser/directory_parser.py"
Task: "T020 — geometry parsers в src/parser/entities/geometry.py"
Task: "T021 — dimension parsers в src/parser/entities/dimensions.py"
Task: "T022 — annotation parsers в src/parser/entities/annotations.py"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Завершить Phase 1: Setup
2. Завершить Phase 2: Foundational (блокирует всё)
3. Завершить Phase 3: US1
4. **ОСТАНОВИТЬСЯ И ПРОВЕРИТЬ**: `POST /parse` с реальным IGES → JSON → отдать в LLM
5. Деплоить / демонстрировать если готово

### Incremental Delivery

1. Setup + Foundational → сервис поднимается, `/health` работает
2. US1 → полный парсинг → MVP готов
3. US2 → надёжная обработка ошибок
4. US3 → обогащение ответа сводкой
5. Каждый шаг добавляет ценность без поломки предыдущего

---

## Notes

- `[P]` = задача работает с независимым файлом, нет незавершённых зависимостей
- Тесты для каждого US пишутся **до** реализации (должны падать → реализация → зелёные)
- Каждый парсер-модуль обязан иметь business-logic комментарии (конституция, Принцип III)
- После каждой фазы сделать коммит
- Остановиться на Checkpoint US1 для валидации с реальным IGES из Компас 3D
