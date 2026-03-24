# Research: IGES File Parser API

**Branch**: `001-iges-parser-api`
**Date**: 2026-03-24

---

## Decision 1: IGES Parsing Strategy

**Decision**: Написать лёгкий кастомный парсер вместо использования pyiges или аналогов.

**Rationale**:
- `pyiges` (v0.3.2, pyvista) ориентирован на 3D-геометрию (B-spline поверхности, VTK-меши)
  и не покрывает 2D-аннотационные сущности (Type 202, 206, 210, 212, 214, 216, 218, 222),
  которые являются основным источником данных для паспорта детали.
- `pyiges` читает из пути к файлу, а не из строки/StringIO.
- IGES-формат — фиксированный ASCII (80 символов на строку), он прост для пошагового
  парсинга: секции разделяются по 73-му символу каждой строки (S/G/D/P/T).
- Кастомный парсер даёт полный контроль над обработкой ошибок, кодировкой (UTF-8/Hollerith)
  и структурой выходного JSON.

**Alternatives considered**:
- `pyiges[full]`: отклонён — фокус на 3D, нет аннотаций, читает файл с диска.
- `iges-reader` (npm-inspired Python ports): не зрелые, нет maintenance.
- Конвертация через Open CASCADE / FreeCAD bindings: слишком тяжёлая зависимость,
  избыточна для задачи извлечения текстовых данных из ASCII-файла.

---

## Decision 2: Обработка Hollerith-строк и кириллицы

**Decision**: Читать входящую строку как Python `str` (уже декодированная UTF-8 от FastAPI).
При парсинге Hollerith-полей (формат `<N>H<текст>`) извлекать текст напрямую как Unicode.

**Rationale**:
- IGES официально ASCII, но Компас 3D записывает кириллицу в Hollerith-поля в CP1251
  или UTF-8 в зависимости от настроек. FastAPI декодирует тело запроса как UTF-8.
- Если клиент передаёт CP1251-контент, он обязан его перекодировать перед отправкой
  (это стандартное поведение HTTP: тело `application/json` всегда UTF-8).
- Тест-кейс: строка `32Hдеталь вал 45 Ra3.2 ГОСТ 21` должна возвращаться без изменений.

**Alternatives considered**:
- Автодетект кодировки через `chardet`: добавляет зависимость и неопределённость.
  Отклонено — ответственность кодировки лежит на клиенте.

---

## Decision 3: Web-фреймворк и ASGI-сервер

**Decision**: FastAPI + Uvicorn с `--workers 4` для ≤5 конкурентных запросов.

**Rationale**:
- FastAPI — конституционное требование (TC-001).
- Uvicorn — стандартный ASGI-сервер для FastAPI в Docker.
- 4 воркера покрывают пик 5 одновременных запросов с запасом при CPU-bound парсинге.
- Дополнительно: Uvicorn можно запустить через Gunicorn с `UvicornWorker` для
  production-grade process management.

**Alternatives considered**:
- Hypercorn: менее распространён, нет преимуществ для данного масштаба.
- Только 1 воркер: не покрывает требование SC-001 при 5 конкурентных запросах.

---

## Decision 4: Структурированное логирование

**Decision**: `structlog` с JSON-рендерером в production, pretty-print в dev.

**Rationale**:
- `structlog` позволяет привязывать контекст (request_id, content_size) к логгеру
  один раз и использовать во всех последующих log-вызовах.
- Интегрируется с Uvicorn/Python standard logging через ProcessorChain.
- В Docker stdout перехватывается оркестратором (Docker Compose, k8s), поэтому
  stdout — правильная цель.
- `orjson` как backend сериализатор опционально ускоряет JSON-логи.

**Alternatives considered**:
- Стандартный `logging` + `json.dumps`: работает, но требует больше boilerplate
  для контекстных полей. Отклонён в пользу structlog.
- `loguru`: популярен, но хуже интегрируется с async FastAPI и Uvicorn.

---

## Decision 5: Ограничение размера запроса

**Decision**: ASGI-middleware проверяет `Content-Length` заголовок + fallback
потоковое чтение; возвращает HTTP 413 при превышении 10 МБ.

**Rationale**:
- FastAPI/Starlette не имеют встроенного лимита на размер тела.
- Проверка `Content-Length` — быстрый путь (клиент честно указывает размер).
- Fallback потокового чтения — защита от клиентов без `Content-Length`.
- NGINX `client_max_body_size` рекомендуется как дополнительный слой в production,
  что отражено в quickstart.md.

**Alternatives considered**:
- Только NGINX: не защищает при прямом обращении к сервису.
- `starlette-validation-uploadfile`: лишняя зависимость для JSON-тела.

---

## Decision 6: Валидация схем запроса/ответа

**Decision**: Pydantic v2 для всех схем запроса, ответа и внутренних моделей.

**Rationale**:
- FastAPI нативно использует Pydantic v2.
- Pydantic v2 значительно быстрее v1 (~10x для валидации).
- `model_json_schema()` позволяет автоматически генерировать OpenAPI-схемы.
- Nested модели (GeometricEntity, DimensionAnnotation) хорошо сериализуются через
  `model.model_dump()`.

---

## Decision 7: Тестирование

**Decision**: `pytest` + `httpx` (через `httpx.AsyncClient` с ASGI transport).

**Rationale**:
- `httpx` с ASGI transport позволяет тестировать FastAPI без запуска реального
  HTTP-сервера — быстро и без сетевых зависимостей.
- Contract-тесты проверяют схему ответа эндпоинта (HTTP-статус, структура JSON).
- Integration-тесты: парсинг реальных IGES-файлов из `tests/fixtures/`.
- Unit-тесты: отдельные парсер-функции для каждого entity type.

---

## IGES Entity Types — Coverage Map

| Type | Название | Категория | Поддержка |
|------|----------|-----------|-----------|
| 100 | Circular Arc | Geometry | ✅ |
| 102 | Composite Curve | Geometry | ✅ |
| 104 | Conic Arc | Geometry | ✅ |
| 106 | Copious Data (Witness Lines) | Geometry | ✅ |
| 110 | Line | Geometry | ✅ |
| 116 | Point | Geometry | ✅ |
| 126 | Rational B-Spline Curve | Geometry | ✅ |
| 202 | Angular Dimension | Dimension | ✅ |
| 206 | Diameter Dimension | Dimension | ✅ |
| 210 | General Label | Annotation | ✅ |
| 212 | General Note | Annotation | ✅ |
| 214 | Leader (Arrow) | Annotation | ✅ |
| 216 | Linear Dimension | Dimension | ✅ |
| 218 | Ordinate Dimension | Dimension | ✅ |
| 222 | Radius Dimension | Dimension | ✅ |
| 230 | Sectioned Area | Geometry | ✅ |
| все прочие | — | Unsupported | записываются в unsupported_entities |
