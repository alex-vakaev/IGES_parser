# API Contract: POST /render

**Service**: IGES File Parser API  
**Branch**: `002-iges-render`  
**Date**: 2026-03-30

## Endpoint

`POST /render`

**Request Content-Type**: `application/json`  
**Accept**: `image/png`, `image/jpeg`, `image/svg+xml`

---

## Request Body

```json
{
  "content": "<IGES text>",
  "format": "png",
  "width_px": 1600,
  "height_px": 1600,
  "dpi": 150,
  "svg_mode": "vector"
}
```

| Field | Type | Required | Notes |
|------|------|----------|-------|
| `content` | string | yes | IGES текст, UTF-8 |
| `format` | string | yes | `png` \| `jpg` \| `svg` |
| `width_px` | int | no | `64..8192`, default `1600` |
| `height_px` | int | no | `64..8192`, default `1600` |
| `dpi` | int | no | `72..600`, default `150` |
| `svg_mode` | string | no | `vector` \| `raster_embedded`, применимо для `svg` |

---

## Success Responses

### 200 OK (PNG)

- `Content-Type: image/png`
- Body: PNG bytes

### 200 OK (JPG)

- `Content-Type: image/jpeg`
- Body: JPEG bytes

### 200 OK (SVG)

- `Content-Type: image/svg+xml`
- Body: SVG text bytes

### Common response headers

| Header | Example | Description |
|--------|---------|-------------|
| `Content-Disposition` | `inline; filename="drawing.png"` | Имя выходного файла |
| `X-Render-Format` | `png` | Фактический формат |
| `X-Render-Size-Bytes` | `234567` | Размер тела ответа |
| `X-Render-Warning` | `near_empty:very_low_visible_primitives` | Присутствует только при деградации |

---

## Error Responses

### 400 EMPTY_INPUT

```json
{
  "detail": {
    "error_code": "EMPTY_INPUT",
    "message": "Поле 'content' не должно быть пустым.",
    "details": {}
  }
}
```

### 400 INVALID_RENDER_OPTIONS

```json
{
  "error_code": "INVALID_RENDER_OPTIONS",
  "message": "Некорректные параметры рендера.",
  "details": {"errors": [{"loc": ["body", "width_px"], "msg": "...", "type": "..."}]}
}
```

### 422 INVALID_FORMAT

```json
{
  "detail": {
    "error_code": "INVALID_FORMAT",
    "message": "Переданный контент не является валидным IGES-файлом.",
    "details": {}
  }
}
```

### 422 RENDER_ERROR

```json
{
  "detail": {
    "error_code": "RENDER_ERROR",
    "message": "Рендер IGES завершился с ошибкой.",
    "details": {}
  }
}
```

### 500 INTERNAL_ERROR

```json
{
  "error_code": "INTERNAL_ERROR",
  "message": "Внутренняя ошибка сервиса. Попробуйте позже.",
  "details": {}
}
```

---

## Contract Testing Scope

1. Проверка всех поддерживаемых `format`.
2. Проверка MIME и обязательных `X-Render-*` заголовков.
3. Проверка warning-header для near-empty случая.
4. Проверка ошибок валидации параметров и пустого input.
