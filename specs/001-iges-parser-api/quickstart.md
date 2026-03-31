# Quickstart: IGES File Parser API

## Требования

- Docker Engine 20.10+
- Docker Compose 2.0+ (опционально, для удобства)
- curl или любой HTTP-клиент для проверки

---

## 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd IGES_parser
```

---

## 2. Переменные окружения

Скопировать пример файла окружения:

```bash
cp .env.example .env
```

Содержимое `.env` (все значения имеют дефолты, `.env` опционален):

| Переменная | Дефолт | Описание |
|------------|--------|----------|
| `APP_HOST` | `0.0.0.0` | Адрес прослушивания |
| `APP_PORT` | `8000` | Порт сервиса |
| `APP_WORKERS` | `4` | Число Uvicorn-воркеров |
| `MAX_CONTENT_BYTES` | `10485760` | Лимит размера запроса (10 МБ) |
| `LOG_LEVEL` | `info` | Уровень логирования: `debug`, `info`, `warning`, `error` |
| `LOG_FORMAT` | `json` | Формат логов: `json` (production) или `pretty` (dev) |

---

## 3. Собрать и запустить через Docker

### Вариант A: Docker Compose

**Продакшн:**
```bash
docker compose up --build -d
```

**Разработка** (с hot-reload и volume mount):
```bash
docker compose -f docker-compose.dev.yml up --build
```

Сервис поднимается в production-конфигурации на `http://localhost` (через Nginx).

Базовый URL по окружению:
- **Production (`docker-compose.yml`)**: `http://localhost`
- **Development (`docker-compose.dev.yml`)**: `http://localhost:8000`

### Вариант B: чистый Docker

```bash
# Сборка образа
docker build -t iges-parser:latest .

# Запуск контейнера
docker run -d \
  --name iges-parser \
  -p 8000:8000 \
  --env-file .env \
  iges-parser:latest
```

---

## 4. Проверка работоспособности

```bash
curl http://localhost/health
```

Ожидаемый ответ:
```json
{"status": "ok"}
```

---

## 5. Отправить IGES-файл на парсинг

### Bash / Linux / macOS

```bash
# Читаем файл в переменную и отправляем как JSON
IGES_CONTENT=$(cat path/to/drawing.igs)

curl -X POST http://localhost/parse \
  -H "Content-Type: application/json" \
  -d "{\"content\": $(echo $IGES_CONTENT | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}"
```

### PowerShell (Windows)

```powershell
$igesContent = Get-Content "path\to\drawing.igs" -Raw

$body = @{ content = $igesContent } | ConvertTo-Json -Depth 1

Invoke-RestMethod -Uri "http://localhost/parse" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

### Python

```python
import json, httpx

with open("drawing.igs", encoding="utf-8") as f:
    content = f.read()

response = httpx.post(
    "http://localhost/parse",
    json={"content": content},
    timeout=30.0
)
print(response.json())
```

---

## 6. Пример успешного ответа

```json
{
  "drawing_metadata": {
    "author": "Иванов И.И.",
    "unit": "mm",
    "drawing_title": "Вал ступенчатый"
  },
  "geometry": [...],
  "dimensions": [...],
  "annotations": [...],
  "summary": {
    "bounding_box": {"min_x": 0, "min_y": -10, "max_x": 200, "max_y": 50},
    "entity_counts": {"line": 42, "circular_arc": 7},
    "total_entities": 66,
    "units": "mm"
  },
  "unsupported_entities": []
}
```

---

## 7. Просмотр логов

```bash
# Docker Compose
docker compose logs -f

# Чистый Docker
docker logs -f iges-parser
```

Каждый запрос пишет строку вида:
```json
{"timestamp":"2026-03-24T17:00:00Z","level":"info","event":"parse_request_completed","http_status":200,"content_size_bytes":45231,"processing_time_ms":312}
```

---

## 8. Остановка

```bash
# Docker Compose
docker compose down

# Чистый Docker
docker stop iges-parser && docker rm iges-parser
```

---

## 9. OpenAPI-документация

После запуска доступна интерактивная документация:

- Swagger UI: `http://localhost/docs`
- ReDoc: `http://localhost/redoc`
- OpenAPI JSON: `http://localhost/openapi.json`

---

## 10. Запуск тестов (без Docker)

```bash
# Установить зависимости
pip install -r requirements.txt

# Запустить все тесты
python -m pytest tests/ -v

# Только contract-тесты (быстрая проверка API-контракта)
python -m pytest tests/contract/ -v
```

---

## Troubleshooting

| Проблема | Вероятная причина | Решение |
|----------|-------------------|---------|
| HTTP 413 | Файл > 10 МБ | Уменьшить файл или увеличить `MAX_CONTENT_BYTES` |
| HTTP 422 `INVALID_FORMAT` | Файл не является IGES или имеет бинарный формат | Убедиться, что файл экспортирован как текстовый IGES |
| HTTP 422 `PARSE_ERROR` | Повреждённые данные в P-секции | Проверить файл в Компас 3D, пересохранить IGES |
| Кириллица отображается кракозябрами | Клиент не перекодировал файл в UTF-8 | Перед отправкой перекодировать: `iconv -f cp1251 -t utf-8 drawing.igs > drawing_utf8.igs` |
| `Connection refused` / `Bad Gateway` | Контейнер или Nginx не запущены | Проверить `docker compose ps`, затем `docker compose logs -f` |
