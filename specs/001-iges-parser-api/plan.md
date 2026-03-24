# Implementation Plan: IGES File Parser API

**Branch**: `001-iges-parser-api` | **Date**: 2026-03-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-iges-parser-api/spec.md`

## Summary

Разработать stateless REST API-сервис на Python/FastAPI, который принимает
текстовое содержимое IGES-файла и возвращает структурированный JSON с геометрией,
размерными аннотациями, текстовыми примечаниями и сводной информацией. Сервис
предназначен для использования в LLM-пайплайне составления паспорта детали.
Парсинг реализуется кастомным парсером (без сторонних IGES-библиотек): IGES —
фиксированный ASCII-формат, прозрачный для посекционного разбора.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI 0.110+, Pydantic v2, Uvicorn, structlog
**Storage**: N/A (stateless, без персистентности)
**Testing**: pytest, httpx (ASGI transport)
**Target Platform**: Linux server (Docker, amd64)
**Project Type**: Backend API service
**Performance Goals**: ≤ 5 сек для файлов до 5 МБ при ≤ 5 конкурентных запросах
**Constraints**: Входной текст UTF-8/ASCII, тело запроса ≤ 10 МБ; нет фронта
**Scale/Scope**: До 5 одновременных запросов; 4 Uvicorn-воркера в Docker

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Использует Python и FastAPI как основной стек (Принцип I)
- [x] Остаётся backend-only, фронт не вводится (Принцип II)
- [x] Определяет API-контракты, валидацию и поведение ошибок (contracts/parse.md)
- [x] Включает Docker-упаковку (Dockerfile + docker-compose.yml в плане задач)
- [x] Включает инструкцию по деплою (quickstart.md создан)
- [x] Новая бизнес-логика (парсер) обозначена как требующая комментариев (Принцип III)
- [x] Обязательные contract и integration тесты запланированы (Принцип IV)

**Post-design re-check**: все ворота пройдены. Нарушений конституции нет.

## Project Structure

### Documentation (this feature)

```text
specs/001-iges-parser-api/
├── plan.md              # Этот файл
├── research.md          # Решения по стеку и инструментам
├── data-model.md        # Схемы всех сущностей
├── quickstart.md        # Инструкция по деплою и проверке
├── contracts/
│   └── parse.md         # Контракт эндпоинта POST /parse
└── tasks.md             # Создаётся командой /speckit.tasks
```

### Source Code (repository root)

```text
src/
├── api/
│   ├── __init__.py
│   ├── router.py          # FastAPI-роутер: POST /parse, GET /health
│   └── schemas.py         # Pydantic-схемы запроса и ответа
├── parser/
│   ├── __init__.py
│   ├── iges_reader.py     # Разбивает IGES-текст на 5 секций
│   ├── global_parser.py   # Парсит Global-секцию → DrawingMetadata
│   ├── directory_parser.py # Читает Directory Entry → карта entity_type → sequence
│   ├── entity_dispatcher.py # Маршрутизирует сущности по типу
│   └── entities/
│       ├── geometry.py    # Types 100, 102, 104, 106, 110, 116, 126, 230
│       ├── dimensions.py  # Types 202, 206, 216, 218, 222
│       └── annotations.py # Types 210, 212, 214
├── models/
│   ├── __init__.py
│   └── internal.py        # Внутренние dataclass-модели parser-слоя
└── core/
    ├── __init__.py
    ├── config.py          # pydantic-settings: env-переменные
    ├── logging.py         # structlog-конфигурация (JSON в prod, pretty в dev)
    └── middleware.py      # ContentSizeLimitMiddleware (HTTP 413)

tests/
├── contract/
│   └── test_parse_endpoint.py   # Тест схемы ответа POST /parse и ошибок
├── integration/
│   └── test_full_parse.py       # Парсинг реальных IGES-файлов из fixtures/
├── unit/
│   ├── test_iges_reader.py      # Разбивка на секции
│   ├── test_global_parser.py    # Парсинг Global-секции
│   └── test_entity_parsers.py   # Каждый тип сущности отдельно
└── fixtures/
    ├── simple_drawing.igs       # Минимальный тестовый IGES
    ├── kompas_sample.igs        # Чертёж из Компас 3D с кириллицей
    └── invalid.txt              # Не-IGES файл для тестирования ошибок

Dockerfile
docker-compose.yml
.env.example
requirements.txt
pyproject.toml
```

**Structure Decision**: Single backend API service. Нет frontend-директории (API-only, Принцип II).
Docker-файлы в корне репозитория, исходный код в `src/`, тесты в `tests/`.

## Architecture Decisions

### Парсинг IGES

Кастомный посекционный парсер:
1. `IgesReader.split_sections(text)` — разбивает текст по символу в позиции 73
   каждой строки (S/G/D/P/T), возвращает 5 сырых секций
2. `GlobalParser.parse(g_section)` → `DrawingMetadata` — разбирает
   comma-delimited параметры Global-секции (P1-P26 по стандарту IGES 5.3)
3. `DirectoryParser.parse(d_section)` → `dict[seq_num, EntityHeader]` —
   читает Directory Entry (2 строки на сущность, фиксированные 8-символьные поля)
4. `EntityDispatcher.dispatch(p_section, directory)` → три списка (geometry,
   dimensions, annotations) + счётчик unsupported — маршрутизирует каждую
   P-запись к нужному парсеру по entity_type из directory

### Ограничение размера запроса

`ContentSizeLimitMiddleware` (ASGI):
- Проверяет `Content-Length` заголовок немедленно (fast path)
- Fallback: читает тело потоком, считая байты
- При превышении 10 МБ — HTTP 413 с `error_code: SIZE_EXCEEDED`

### Логирование

`structlog` ProcessorChain:
- `LOG_FORMAT=json` → `JSONRenderer` (production/Docker)
- `LOG_FORMAT=pretty` → `ConsoleRenderer` (local dev)
- Middleware добавляет в контекст: `request_id`, `content_size_bytes`
- После обработки логирует: `http_status`, `processing_time_ms`, `entity_count`

### Конфигурация

`pydantic-settings` читает переменные окружения из `.env`:
`APP_HOST`, `APP_PORT`, `APP_WORKERS`, `MAX_CONTENT_BYTES`, `LOG_LEVEL`, `LOG_FORMAT`

## Complexity Tracking

Нарушений конституции нет. Таблица не требуется.

## Phases (for /speckit.tasks reference)

### Phase 1: Setup

Инициализация проекта, зависимости, Docker-сборка.

### Phase 2: Foundational

Core-инфраструктура: конфигурация, логирование, middleware, базовая структура FastAPI,
health-эндпоинт. Блокирует все пользовательские сценарии.

### Phase 3: US1 — Parse IGES → Structured JSON (P1, MVP)

Полный парсинг: IgesReader → GlobalParser → DirectoryParser → EntityDispatcher
(geometry + dimensions + annotations) → DrawingSummary. Эндпоинт POST /parse.
Contract-тест + integration-тест.

### Phase 4: US2 — Error Handling (P2)

Валидация входных данных: EMPTY_INPUT, INVALID_FORMAT, SIZE_EXCEEDED, PARSE_ERROR.
Тесты ошибочных сценариев.

### Phase 5: US3 — Drawing Summary (P3)

BoundingBox по координатам геометрии, entity_counts, units. Уже частично в Phase 3;
отдельные unit-тесты для логики вычисления summary.

### Phase N: Polish

Docker-финализация, deployment guide validation, документация, security hardening.
