# Data Model: IGES Render Endpoint

**Branch**: `002-iges-render`  
**Date**: 2026-03-30

## 1) RenderRequest

Входная модель запроса рендера.

| Field | Type | Required | Rules |
|------|------|----------|-------|
| `content` | string | yes | Полный IGES-текст, не пустой |
| `format` | enum | yes | `png` \| `jpg` \| `svg` |
| `width_px` | integer | no | `64..8192`, default `1600` |
| `height_px` | integer | no | `64..8192`, default `1600` |
| `dpi` | integer | no | `72..600`, default `150` |
| `svg_mode` | enum | no | `vector` \| `raster_embedded`, default `vector` (только для `format=svg`) |

### Validation rules

- `content` пустой -> `EMPTY_INPUT`.
- Неподдерживаемый `format` -> `UNSUPPORTED_RENDER_FORMAT`.
- Параметры вне диапазона -> `INVALID_RENDER_OPTIONS`.
- Для `format=svg` допускается `svg_mode`; для raster форматов параметр игнорируется.

## 2) RenderResult (HTTP response + headers)

Тело ответа содержит бинарный файл изображения.

### Response body

- `image/png` -> bytes PNG
- `image/jpeg` -> bytes JPEG
- `image/svg+xml` -> bytes SVG document

### Response headers

| Header | Purpose | Example |
|--------|---------|---------|
| `Content-Type` | MIME результата | `image/png` |
| `Content-Disposition` | Имя файла | `inline; filename="drawing.png"` |
| `X-Render-Format` | Фактический формат | `png` |
| `X-Render-Size-Bytes` | Размер результата | `234567` |
| `X-Render-Warning` | Warning код+текст при деградации | `near_empty:very_low_visible_primitives` |

## 3) RenderWarning

Внутренняя модель классификации результата рендера.

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | `empty` \| `near_empty` \| `degraded` |
| `message` | string | Короткое объяснение для клиента |
| `metrics` | object | Служебные измерения (например, доля видимых примитивов) |

## 4) RenderError

Структура ошибок рендера (JSON при 4xx/5xx).

| Field | Type | Description |
|-------|------|-------------|
| `error_code` | string | `EMPTY_INPUT` \| `UNSUPPORTED_RENDER_FORMAT` \| `INVALID_RENDER_OPTIONS` \| `INVALID_FORMAT` \| `RENDER_ERROR` \| `INTERNAL_ERROR` |
| `message` | string | Человекочитаемое сообщение |
| `details` | object | Диагностические поля |

## 5) Relationship notes

- `RenderRequest` -> `RenderResult` (1:1, synchronous)
- `RenderResult` может иметь 0..1 `RenderWarning` (передаётся через заголовок)
- `RenderRequest` при сбое -> `RenderError`
