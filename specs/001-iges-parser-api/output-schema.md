# Структура выходного JSON парсера IGES

Описание полей ответа `POST /parse` для передачи LLM в качестве системного контекста.

---

## Корневой объект

```json
{
  "drawing_metadata": { ... },
  "geometry":         [ ... ],
  "dimensions":       [ ... ],
  "annotations":      [ ... ],
  "summary":          { ... },
  "unsupported_entities": [ ... ]
}
```

---

## `drawing_metadata` — метаданные чертежа

Извлекается из Global-секции IGES (параметры P1–P26). Все поля опциональны (`null` если не указаны в файле).

| Поле | Тип | Описание |
|---|---|---|
| `author` | `string\|null` | Автор / конструктор (P21) |
| `organization` | `string\|null` | Организация-разработчик (P22) |
| `created_at` | `string\|null` | Дата создания (P18, формат IGES: `YYYYMMDD:HHMMSS`) |
| `modified_at` | `string\|null` | Дата последнего изменения (P25) |
| `drawing_title` | `string\|null` | Обозначение чертежа / путь к исходному файлу (P4) |
| `unit` | `string` | Единицы измерения: `"mm"`, `"inches"`, `"cm"`, `"meters"` и др. По умолчанию `"unknown"` |
| `unit_code` | `int\|null` | Числовой код единицы по IGES (P14): `1`=дюймы, `2`=мм, `5`=м и т.д. |
| `scale` | `float\|null` | Масштаб чертежа — Model Space Scale (P13) |
| `iges_version` | `string\|null` | Версия стандарта IGES (P23) |
| `drafting_standard` | `string\|null` | Стандарт оформления (P24): `"ISO"`, `"ANSI"`, `"DIN"` и др. |

---

## `geometry` — геометрические примитивы

Массив объектов. Каждый объект описывает один геометрический или служебный элемент чертежа.

### Поля объекта

| Поле | Тип | Описание |
|---|---|---|
| `entity_type` | `int` | Числовой тип сущности по IGES |
| `entity_name` | `string` | Читаемое имя типа (см. таблицу ниже) |
| `sequence_number` | `int` | Порядковый номер в D-секции IGES (нечётное число) |
| `layer` | `int\|null` | Слой чертежа |
| `color` | `int\|null` | Цвет: `-1` = по умолчанию, `≥1` = указатель DE на `color_definition` |
| `line_weight` | `int\|null` | Толщина линии |
| `coordinates` | `object` | Тип-специфичные данные (см. таблицу ниже) |
| `raw_parameters` | `string[]` | Исходные строки параметров из P-секции IGES |

### Типы сущностей и структура `coordinates`

| `entity_name` | IGES тип | Структура `coordinates` |
|---|---|---|
| `line` | 110 | `{ start: {x, y, z}, end: {x, y, z} }` |
| `circular_arc` | 100 | `{ plane_z, center: {x, y}, start: {x, y}, end: {x, y} }` |
| `conic_arc` | 104 | `{ a, b, c, d, e, f, z_plane, start: {x, y}, end: {x, y} }` — коэффициенты уравнения A·x²+B·xy+C·y²+D·x+E·y+F=0 |
| `copious_data` | 106 | IP=1: `{ form, common_z, points: [{x,y},...] }` / IP=2: `{ form, points: [{x,y,z},...] }` — выносные линии размеров |
| `composite_curve` | 102 | `{ component_count, component_sequence_numbers: [int,...] }` |
| `b_spline_curve` | 126 | `{ degree, knot_count, control_points: [{x, y, z},...] }` |
| `point` | 116 | `{ x, y, z }` |
| `sectioned_area` | 230 | `{ boundary_sequence_number, hatch_pattern, hatch_angle }` — штриховка/сечение |
| `color_definition` | 314 | `{ r, g, b }` — RGB в диапазоне 0–100 (не 0–255) |
| `associativity_group` | 402 | `{ member_count, member_sequence_numbers: [int,...] }` — логическая группа сущностей |

---

## `dimensions` — размерные аннотации

Массив объектов. Каждый объект описывает один размер, проставленный на чертеже.

### Поля объекта

| Поле | Тип | Описание |
|---|---|---|
| `entity_type` | `int` | Числовой тип по IGES |
| `dimension_type` | `string` | `"linear"` / `"angular"` / `"radial"` / `"diameter"` / `"ordinate"` |
| `sequence_number` | `int` | Порядковый номер в D-секции |
| `value` | `float\|null` | Числовое значение размера, извлечённое из текста |
| `text_display` | `string\|null` | Строка «как на чертеже»: `"30"`, `"R12.5"`, `"Ø25"`, `"45°"`, `"3×12"` |
| `unit` | `string\|null` | Единица измерения размера |
| `arrow_coordinates` | `object[]\|null` | Координаты стрелок-выносок |
| `raw_parameters` | `string[]` | Исходные параметры |

### Соответствие типов IGES

| IGES тип | `dimension_type` | Описание |
|---|---|---|
| 202 | `angular` | Угловой размер |
| 206 | `diameter` | Диаметральный размер |
| 216 | `linear` | Линейный размер |
| 218 | `ordinate` | Ординатный размер |
| 222 | `radial` | Радиусный размер |

---

## `annotations` — текстовые аннотации

Массив объектов. Все текстовые надписи чертежа: шероховатости, допуски, марки материала, технические требования, основная надпись.

### Поля объекта

| Поле | Тип | Описание |
|---|---|---|
| `entity_type` | `int` | `212` (General Note) или `210` (General Label) |
| `entity_name` | `string` | `"general_note"` или `"general_label"` |
| `sequence_number` | `int` | Порядковый номер |
| `content` | `string` | **Текст аннотации** — основное поле для LLM |
| `position_x` | `float\|null` | X-координата точки вставки текста |
| `position_y` | `float\|null` | Y-координата точки вставки текста |
| `char_height` | `float\|null` | Высота символов (в единицах чертежа) |
| `raw_parameters` | `string[]` | Исходные параметры |

### Что содержит поле `content`

- Шероховатость поверхности: `"Ra 0,80"`, `"Ra 1,6"`, `"Rz 20"`
- Допуски: `"H14"`, `"h6"`, `"H14, h14, ±IT14/2"`
- Марка материала: `"Сталь 6ХВ2С ГОСТ 5950-2000"`
- Обозначение позиции / детали: `"07-54-105-01"`, `"Фланец"`
- Технические требования: `"Маркировать ударным способом: обозначение, дата изготовления."`
- Надписи основной надписи: `"Масса"`, `"Масштаб"`, `"1:1"`, `"Формат"`, `"A3"` и т.д.
- Размерные значения, связанные с `dimensions`: `"30"`, `"R1"`, `"4,26"`, `"3 отв."`

---

## `summary` — сводка

| Поле | Тип | Описание |
|---|---|---|
| `bounding_box` | `object\|null` | `{ min_x, min_y, max_x, max_y }` — минимальный описывающий прямоугольник по всей геометрии |
| `entity_counts` | `object` | Словарь `entity_name → count`, например `{"line": 120, "circular_arc": 15, "general_note": 80}` |
| `total_entities` | `int` | Суммарное число всех разобранных сущностей (geometry + dimensions + annotations) |
| `units` | `string` | Единицы измерения (дублирует `drawing_metadata.unit`) |

---

## `unsupported_entities` — нераспознанные типы

Массив объектов `{ entity_type: int, count: int }`.

В норме пустой. Если не пуст — тип IGES не поддерживается текущей версией парсера. Используется для диагностики и планирования доработок.

---

## Рекомендуемый системный промпт для LLM

```
Ты получаешь структурированный JSON IGES-чертежа детали.

Ключевые поля:

1. drawing_metadata — контекст чертежа.
   Важно: unit — единицы измерения всех координат и размеров.

2. summary.bounding_box — габаритный прямоугольник детали {min_x, min_y, max_x, max_y}.
   Все значения в drawing_metadata.unit.

3. dimensions[] — размеры детали.
   Читай text_display («как на чертеже»): "30", "R12.5", "Ø25", "3×12".
   value — извлечённое числовое значение.
   dimension_type: linear | angular | radial | diameter | ordinate.

4. annotations[] — все текстовые надписи.
   Поле content содержит:
   - шероховатость (Ra X,X / Rz XX)
   - допуски посадочных мест (H14, h6, ±IT14/2)
   - марку материала и ГОСТ
   - технические требования
   - позиции и обозначения
   Используй content для составления паспорта детали.

5. geometry[] — геометрические примитивы.
   entity_name определяет тип: line, circular_arc, copious_data и т.д.
   color — числовой указатель на сущность color_definition в том же массиве.

6. unsupported_entities[] — типы, не распознанные парсером (для диагностики).

Все координаты и размеры — в единицах drawing_metadata.unit.
```
