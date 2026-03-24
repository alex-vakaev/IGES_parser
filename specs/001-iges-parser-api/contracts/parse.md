# API Contract: POST /parse

**Service**: IGES File Parser API
**Branch**: `001-iges-parser-api`
**Date**: 2026-03-24

---

## Endpoint

```
POST /parse
```

**Content-Type**: `application/json`
**Accept**: `application/json`

---

## Request

### Headers

| Header | Значение | Обязательно |
|--------|----------|-------------|
| `Content-Type` | `application/json` | да |
| `Content-Length` | размер тела в байтах | рекомендуется |

### Body Schema

```json
{
  "content": "<полное текстовое содержимое IGES-файла>"
}
```

| Поле | Тип | Ограничения |
|------|-----|-------------|
| `content` | string | обязательно; непустая строка; тело запроса ≤ 10 МБ |

### Пример запроса

```json
{
  "content": "                                                                        S      1\n1H,,1H;,7Htest.igs,28HKompas-3D 21.0 (c) ASCON 2022,..."
}
```

*Поле `options` отсутствует — raw-параметры включаются в ответ всегда.*

---

## Responses

### 200 OK — успешный парсинг

```json
{
  "drawing_metadata": {
    "author": "Иванов И.И.",
    "organization": "ООО Завод",
    "created_at": "2024-05-15",
    "modified_at": null,
    "drawing_title": "Вал ступенчатый",
    "unit": "mm",
    "unit_code": 2,
    "scale": 1.0,
    "iges_version": "5.3",
    "drafting_standard": "GOST"
  },
  "geometry": [
    {
      "entity_type": 110,
      "entity_name": "line",
      "sequence_number": 1,
      "layer": 0,
      "color": 1,
      "line_weight": 2,
      "coordinates": {
        "start": {"x": 0.0, "y": 0.0, "z": 0.0},
        "end":   {"x": 100.0, "y": 0.0, "z": 0.0}
      },
      "raw_parameters": ["110", "0.0", "0.0", "0.0", "100.0", "0.0", "0.0"]
    }
  ],
  "dimensions": [
    {
      "entity_type": 216,
      "dimension_type": "linear",
      "sequence_number": 15,
      "value": 100.0,
      "unit": "mm",
      "text_display": "100",
      "arrow_coordinates": [
        {"x": 0.0, "y": -5.0},
        {"x": 100.0, "y": -5.0}
      ],
      "raw_parameters": ["216", "15", "17", "0", "0"]
    }
  ],
  "annotations": [
    {
      "entity_type": 212,
      "entity_name": "general_note",
      "sequence_number": 17,
      "content": "Ra 3.2",
      "position_x": 50.0,
      "position_y": 10.0,
      "char_height": 3.5,
      "raw_parameters": ["212", "1", "6", "3.5", "0.0", "0.0", "1.0", "0.0", "0.0", "6HRa 3.2"]
    }
  ],
  "summary": {
    "bounding_box": {
      "min_x": 0.0,
      "min_y": -10.0,
      "max_x": 200.0,
      "max_y": 50.0
    },
    "entity_counts": {
      "line": 42,
      "circular_arc": 7,
      "linear_dimension": 12,
      "general_note": 5
    },
    "total_entities": 66,
    "units": "mm"
  },
  "unsupported_entities": [
    {"entity_type": 406, "count": 2}
  ]
}
```

---

### 400 Bad Request — пустой или отсутствующий контент

```json
{
  "error_code": "EMPTY_INPUT",
  "message": "Поле 'content' обязательно и не должно быть пустым.",
  "details": {}
}
```

**Триггер**: поле `content` отсутствует или содержит пустую строку.

---

### 413 Content Too Large — превышен лимит размера

```json
{
  "error_code": "SIZE_EXCEEDED",
  "message": "Размер запроса превышает допустимый лимит 10 МБ.",
  "details": {
    "max_bytes": 10485760,
    "received_bytes": 12500000
  }
}
```

**Триггер**: тело запроса > 10 МБ (определяется middleware по `Content-Length` или потоковым чтением).

---

### 422 Unprocessable Entity — контент не является IGES

```json
{
  "error_code": "INVALID_FORMAT",
  "message": "Переданный контент не является валидным IGES-файлом.",
  "details": {
    "reason": "Start section (S) not found in first 100 lines"
  }
}
```

**Триггер**: структура секций IGES не распознана (отсутствует Start- или Global-секция).

---

### 422 Unprocessable Entity — ошибка при парсинге

```json
{
  "error_code": "PARSE_ERROR",
  "message": "Ошибка при разборе параметров сущности.",
  "details": {
    "entity_type": 216,
    "sequence_number": 15,
    "reason": "Expected float at parameter index 3, got 'abc'"
  }
}
```

**Триггер**: валидный IGES, но данные конкретной сущности повреждены.

---

### 500 Internal Server Error

```json
{
  "error_code": "INTERNAL_ERROR",
  "message": "Внутренняя ошибка сервиса. Попробуйте позже.",
  "details": {}
}
```

**Триггер**: непредвиденное исключение (details не раскрываются клиенту, фиксируются в логах).

---

## Дополнительный эндпоинт

### GET /health

Проверка работоспособности сервиса.

**Response 200**:
```json
{"status": "ok"}
```

---

## Ограничения

| Параметр | Значение |
|----------|----------|
| Максимальный размер запроса | 10 МБ |
| Максимальное время обработки | 30 секунд (Uvicorn timeout) |
| Конкурентных запросов | до 5 (4 воркера Uvicorn) |
| Кодировка тела запроса | UTF-8 |

---

## Логирование каждого запроса

Сервис пишет структурированный JSON-лог в stdout для каждого запроса:

```json
{
  "timestamp": "2026-03-24T17:00:00Z",
  "level": "info",
  "event": "parse_request_completed",
  "http_status": 200,
  "content_size_bytes": 45231,
  "processing_time_ms": 312,
  "entity_count": 66
}
```

При ошибке добавляются поля `error_code` и `error_detail`.
