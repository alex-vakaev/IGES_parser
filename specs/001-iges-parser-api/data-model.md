# Data Model: IGES File Parser API

**Branch**: `001-iges-parser-api`
**Date**: 2026-03-24

Все схемы реализуются через Pydantic v2. Внутренние модели (parser layer)
могут отличаться от API-схем; финальная сериализация идёт через API-схемы.

---

## Входящие данные

### `ParseRequest`

Тело POST-запроса на `/parse`.

| Поле | Тип | Обязательно | Описание |
|------|-----|-------------|----------|
| `content` | `str` | да | Полное текстовое содержимое IGES-файла (UTF-8) |

Валидация:
- `content` не должен быть пустой строкой → `EMPTY_INPUT`
- Размер тела запроса ≤ 10 МБ (проверяется middleware) → `SIZE_EXCEEDED`
- `content` должен начинаться хотя бы с одной строки, оканчивающейся на `S` в позиции 73 → `INVALID_FORMAT`

---

## Исходящие данные

### `ParseResponse`

Корневой объект успешного ответа (HTTP 200).

| Поле | Тип | Описание |
|------|-----|----------|
| `drawing_metadata` | `DrawingMetadata` | Метаданные из Global-секции |
| `geometry` | `list[GeometricEntity]` | Геометрические примитивы |
| `dimensions` | `list[DimensionAnnotation]` | Размерные аннотации |
| `annotations` | `list[TextAnnotation]` | Текстовые примечания и метки |
| `summary` | `DrawingSummary` | Сводка: bounding box, счётчики, единицы |
| `unsupported_entities` | `list[UnsupportedEntityRecord]` | Типы сущностей вне поддержки |

---

### `DrawingMetadata`

Извлекается из секции Global (G) IGES-файла.

| Поле | Тип | IGES Global поле | Описание |
|------|-----|-----------------|----------|
| `author` | `str \| None` | P11 | Автор чертежа |
| `organization` | `str \| None` | P12 | Организация |
| `created_at` | `str \| None` | P18 | Дата создания (ISO-формат или строка из файла) |
| `modified_at` | `str \| None` | P19 | Дата последнего изменения |
| `drawing_title` | `str \| None` | P4 (sending system) | Обозначение/наименование чертежа |
| `unit` | `str` | P14 | Единица измерения: `mm`, `inches`, `cm`, `unknown` |
| `unit_code` | `int \| None` | P14 raw | Исходный код единицы из файла |
| `scale` | `float \| None` | P13 | Масштаб (например, 1.0, 2.0) |
| `iges_version` | `str \| None` | P23 | Версия IGES |
| `drafting_standard` | `str \| None` | P24 | Стандарт оформления (ГОСТ, ISO, ANSI) |

---

### `GeometricEntity`

Одна геометрическая сущность из секции Parameter Data.

| Поле | Тип | Описание |
|------|-----|----------|
| `entity_type` | `int` | Номер типа сущности по IGES (100, 110, 126, ...) |
| `entity_name` | `str` | Читаемое имя: `circular_arc`, `line`, `b_spline_curve`, ... |
| `sequence_number` | `int` | Номер строки в Directory Entry |
| `layer` | `int \| None` | Слой/уровень (Level, DE field 5) |
| `color` | `int \| None` | Код цвета (DE field 13) |
| `line_weight` | `int \| None` | Толщина линии (DE field 12) |
| `coordinates` | `dict` | Тип-специфичные координаты (см. ниже) |
| `raw_parameters` | `list[str]` | Исходные параметры из P-секции (строки через запятую) |

**Структура `coordinates` по типам:**

- Type 110 (Line): `{start: {x, y, z}, end: {x, y, z}}`
- Type 100 (Circular Arc): `{center: {x, y}, start_angle_deg, end_angle_deg, radius}`
- Type 104 (Conic Arc): `{a, b, c, d, e, f, x1, y1, x2, y2, z_plane}`
- Type 102 (Composite Curve): `{component_count, component_sequence_numbers: [int]}`
- Type 106 (Copious Data): `{form, points: [{x, y, z}]}`
- Type 116 (Point): `{x, y, z}`
- Type 126 (B-Spline Curve): `{degree, knot_count, control_points: [{x, y, z}]}`
- Type 230 (Sectioned Area): `{boundary_sequence_number, hatch_pattern, hatch_angle}`

---

### `DimensionAnnotation`

Размерная аннотация (линейный, угловой, радиусный, диаметральный, ординатный размер).

| Поле | Тип | Описание |
|------|-----|----------|
| `entity_type` | `int` | IGES тип: 202, 206, 216, 218, 222 |
| `dimension_type` | `str` | `angular`, `diameter`, `linear`, `ordinate`, `radius` |
| `sequence_number` | `int` | Номер строки в DE |
| `value` | `float \| None` | Числовое значение размера (если удалось извлечь) |
| `unit` | `str \| None` | Единица (наследуется из DrawingMetadata.unit) |
| `text_display` | `str \| None` | Текстовое представление «как на чертеже» (из linked General Note) |
| `arrow_coordinates` | `list[dict] \| None` | Координаты стрелок/точек привязки |
| `raw_parameters` | `list[str]` | Исходные параметры P-секции |

---

### `TextAnnotation`

Текстовое примечание или метка.

| Поле | Тип | Описание |
|------|-----|----------|
| `entity_type` | `int` | 210 (General Label) или 212 (General Note) |
| `entity_name` | `str` | `general_label` или `general_note` |
| `sequence_number` | `int` | Номер строки в DE |
| `content` | `str` | Полный текст примечания (Unicode, кириллица сохраняется) |
| `position_x` | `float \| None` | Координата X текстового блока |
| `position_y` | `float \| None` | Координата Y текстового блока |
| `char_height` | `float \| None` | Высота символов |
| `raw_parameters` | `list[str]` | Исходные параметры P-секции |

---

### `DrawingSummary`

Предрассчитанная сводка по всему чертежу.

| Поле | Тип | Описание |
|------|-----|----------|
| `bounding_box` | `Optional[BoundingBox]` | Габариты чертёжного поля; `null` если в файле нет геометрии с координатами |
| `entity_counts` | `dict[str, int]` | Счётчик по типам: `{"line": 42, "circular_arc": 7, ...}` |
| `total_entities` | `int` | Общее число распарсенных сущностей |
| `units` | `str` | Единица измерения (из DrawingMetadata.unit) |

### `BoundingBox`

| Поле | Тип | Описание |
|------|-----|----------|
| `min_x` | `float` | Минимальная X-координата по всей геометрии |
| `min_y` | `float` | Минимальная Y-координата |
| `max_x` | `float` | Максимальная X-координата |
| `max_y` | `float` | Максимальная Y-координата |

---

### `UnsupportedEntityRecord`

Запись о встреченном, но не поддерживаемом типе сущности.

| Поле | Тип | Описание |
|------|-----|----------|
| `entity_type` | `int` | Номер типа сущности |
| `count` | `int` | Количество вхождений в файле |

---

## Ошибочный ответ

### `ErrorResponse`

HTTP 400 / 413 / 422 / 500.

| Поле | Тип | Описание |
|------|-----|----------|
| `error_code` | `str` | `EMPTY_INPUT`, `INVALID_FORMAT`, `SIZE_EXCEEDED`, `PARSE_ERROR`, `INTERNAL_ERROR` |
| `message` | `str` | Человекочитаемое описание ошибки |
| `details` | `dict` | Дополнительный контекст (секция файла, номер строки, тип сущности и т.д.) |

---

## Отношения между сущностями

```
ParseRequest
    └── content: str (raw IGES text)

ParseResponse
    ├── drawing_metadata: DrawingMetadata     (1:1, Global section)
    ├── geometry: [GeometricEntity]            (0..N, P-section types 100-230)
    ├── dimensions: [DimensionAnnotation]     (0..N, P-section types 202-222)
    ├── annotations: [TextAnnotation]         (0..N, P-section types 210, 212)
    ├── summary: DrawingSummary               (1:1, computed)
    │       └── bounding_box: BoundingBox     (1:1, computed from geometry coords)
    └── unsupported_entities: [UnsupportedEntityRecord]  (0..N)
```

DimensionAnnotation.text_display ← связан с TextAnnotation через DE pointer
(entity pointer в параметрах dimension entity ссылается на General Note).
