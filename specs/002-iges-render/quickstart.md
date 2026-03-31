# Quickstart: IGES Render Endpoint

## Требования

- Docker Engine 20.10+
- Docker Compose 2.0+
- curl / PowerShell / Python client

## 1. Запуск сервиса

```bash
docker compose up --build -d
```

Production base URL: `http://localhost`

Для локальной разработки (hot-reload) используйте:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Development base URL: `http://localhost:8000`

Проверка:

```bash
curl http://localhost/health
```

## 2. Рендер в PNG

### PowerShell

```powershell
$iges = Get-Content "tests\fixtures\simple_drawing.igs" -Raw
$body = @{
  content = $iges
  format = "png"
  width_px = 1600
  height_px = 1600
  dpi = 150
} | ConvertTo-Json -Depth 3

Invoke-WebRequest -Uri "http://localhost/render" -Method POST -ContentType "application/json" -Body $body -OutFile "drawing.png"
```

### curl

```bash
curl -X POST http://localhost/render \
  -H "Content-Type: application/json" \
  -H "Accept: image/png" \
  -d @render-request.json \
  -o drawing.png -D headers.txt
```

Для dev-режима замените `http://localhost` на `http://localhost:8000` во всех примерах.

`render-request.json`:

```json
{
  "content": "<IGES_TEXT>",
  "format": "png",
  "width_px": 1600,
  "height_px": 1600,
  "dpi": 150
}
```

## 3. Рендер в JPG

Заменить `format` на `jpg` и `Accept` на `image/jpeg`.

## 4. Рендер в SVG (vector)

```json
{
  "content": "<IGES_TEXT>",
  "format": "svg",
  "svg_mode": "vector"
}
```

## 5. Рендер в SVG (embedded raster)

```json
{
  "content": "<IGES_TEXT>",
  "format": "svg",
  "svg_mode": "raster_embedded",
  "width_px": 1600,
  "height_px": 1600,
  "dpi": 150
}
```

## 6. Проверка заголовков

Ожидаемые заголовки в успешном ответе:

- `X-Render-Format`
- `X-Render-Size-Bytes`
- `X-Render-Warning` (только если near-empty/empty)

## 7. Типовые ошибки

- `EMPTY_INPUT` — пустой `content`
- `INVALID_RENDER_OPTIONS` — параметры вне диапазона
- `INVALID_FORMAT` — не IGES
- `RENDER_ERROR` — ошибка движка рендера

## 8. Проверка для деплоя

1. `POST /render` возвращает корректный `Content-Type`.
2. Файл открывается локально (PNG/JPG/SVG).
3. В near-empty кейсе присутствует `X-Render-Warning`.
4. Ошибки возвращаются структурированным JSON.

## 9. Регрессионный набор и метрика успешности (SC-002)

Рекомендуемый минимальный набор:

- `tests/fixtures/simple_drawing.igs`
- `tests/fixtures/kompas_sample.igs`
- `tests/fixtures/534.igs`

Правило подсчёта успешности:

1. Для каждого файла выполнить рендер в `png`, `jpg`, `svg`.
2. Успешным считать прогон, если:
   - HTTP 200,
   - корректный `Content-Type`,
   - размер тела > 0.
3. Метрика SC-002 = `successful_runs / total_runs * 100%`, целевой порог >= 95%.

## 10. Проверка p95 latency <= 3s (SC-003)

Простой сценарий измерения:

1. Выполнить 50 последовательных запросов `POST /render` на среднем файле (например, `534.igs`) с дефолтами PNG.
2. Для каждого запроса фиксировать `processing_time_ms` из логов сервиса.
3. Отсортировать измерения и вычислить p95.
4. Критерий прохождения: p95 <= 3000 ms.
