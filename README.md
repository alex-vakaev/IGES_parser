# IGES Parser API

REST API сервис для парсинга IGES-файлов (технических чертежей) в структурированный JSON.

## Возможности

- Извлечение метаданных чертежа (автор, единицы, масштаб, дата)
- Парсинг геометрических примитивов: отрезки (110), дуги (100), полилинии (106), точки (116)
- Парсинг размеров: линейные (206), угловые (202), диаметральные (216), радиальные (218)
- Парсинг текстовых аннотаций: General Note (212), General Label (210)
- Поддержка Color Definition (314) и Associativity Instance (402)
- Автоматическое вычисление bounding box и сводной статистики по сущностям

## Быстрый старт

```bash
git clone https://github.com/alex-vakaev/IGES_parser.git
cd IGES_parser
cp .env.example .env
docker compose up --build
```

Базовый URL зависит от режима запуска:

- Production (`docker-compose.yml` + Nginx): `http://localhost`
- Development (`docker-compose.dev.yml`, прямой Uvicorn): `http://localhost:8000`

## Использование

### PowerShell

```powershell
$body = @{ content = (Get-Content "drawing.igs" -Raw) } | ConvertTo-Json -Depth 1
Invoke-RestMethod -Uri "http://localhost/parse" -Method POST -ContentType "application/json" -Body $body
```

### Python

```python
import httpx

with open("drawing.igs", encoding="utf-8") as f:
    content = f.read()

response = httpx.post("http://localhost/parse", json={"content": content})
print(response.json())
```

### Рендер в PNG/JPG/SVG

```python
import httpx

with open("drawing.igs", encoding="utf-8") as f:
    content = f.read()

response = httpx.post(
    "http://localhost/render",
    json={
        "content": content,
        "format": "png",
        "width_px": 1600,
        "height_px": 1600,
        "dpi": 150,
    },
    timeout=60.0,
)
print(response.status_code, response.headers.get("content-type"))
open("drawing.png", "wb").write(response.content)
```

### Проверка работоспособности

```bash
curl http://localhost/health
# {"status": "ok"}
```

## Структура ответа

```json
{
  "drawing_metadata": { "author": "...", "unit": "mm", "drawing_title": "..." },
  "geometry": [...],
  "dimensions": [...],
  "annotations": [...],
  "summary": {
    "bounding_box": { "min_x": 0, "min_y": -10, "max_x": 200, "max_y": 50 },
    "entity_counts": { "line": 42, "circular_arc": 7 },
    "total_entities": 66,
    "units": "mm"
  },
  "unsupported_entities": []
}
```

Полное описание схемы: [`specs/001-iges-parser-api/output-schema.md`](specs/001-iges-parser-api/output-schema.md)

## Документация

- Swagger UI: `http://localhost/docs`
- ReDoc: `http://localhost/redoc`
- Подробный quickstart: [`specs/001-iges-parser-api/quickstart.md`](specs/001-iges-parser-api/quickstart.md)

## Переменные окружения

| Переменная | Дефолт | Описание |
|------------|--------|----------|
| `APP_PORT` | `8000` | Порт сервиса |
| `APP_WORKERS` | `4` | Число Uvicorn-воркеров |
| `MAX_CONTENT_BYTES` | `10485760` | Лимит размера запроса (10 МБ) |
| `LOG_LEVEL` | `info` | Уровень логирования |
| `LOG_FORMAT` | `json` | Формат логов: `json` или `pretty` |

## Технологии

- [FastAPI](https://fastapi.tiangolo.com/) + [Pydantic v2](https://docs.pydantic.dev/)
- [Uvicorn](https://www.uvicorn.org/) ASGI-сервер
- [structlog](https://www.structlog.org/) для структурированного логирования
- Docker / Docker Compose

## Тесты

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```
