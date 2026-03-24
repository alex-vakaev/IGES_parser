from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.router import router
from src.core.logging import configure_logging, get_logger
from src.core.middleware import ContentSizeLimitMiddleware, RequestLoggingMiddleware

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle-хук: логируем старт и остановку сервиса."""
    logger.info("service_started", version="1.0.0")
    yield
    logger.info("service_stopped")


app = FastAPI(
    title="IGES File Parser API",
    description="Парсит IGES-файлы инженерных чертежей и возвращает структурированный JSON для LLM-пайплайна.",
    version="1.0.0",
    lifespan=lifespan,
)

# Порядок важен: сначала размер, потом логирование
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ContentSizeLimitMiddleware)

app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Перехватывает ошибки валидации запроса.

    Если ошибка — невалидный JSON (например, необработанные обратные слэши
    из Windows-путей в IGES-файлах), возвращает понятный 400 с инструкцией.
    Остальные ошибки валидации возвращаем как стандартные 422.
    """
    errors = exc.errors()
    is_json_parse_error = any(e.get("type") == "json_invalid" for e in errors)

    if is_json_parse_error:
        # Ищем позицию в теле, где JSON-парсер упал
        error_pos = None
        for err in errors:
            loc = err.get("loc", [])
            if len(loc) > 1 and isinstance(loc[1], int):
                error_pos = loc[1]
                break
        return JSONResponse(
            status_code=400,
            content={
                "error_code": "INVALID_JSON",
                "message": (
                    "Тело запроса содержит некорректный JSON. "
                    "Возможная причина: содержимое IGES-файла вставлено напрямую без JSON-сериализации. "
                    "Обратные слэши (например, в Windows-путях вида S:\\path\\file) "
                    "должны быть экранированы как \\\\ в JSON-строке. "
                    "Используйте JSON-сериализатор: Python — json.dumps(), "
                    "PowerShell — ConvertTo-Json, Postman — поле Body > raw > JSON."
                ),
                "details": {"position": error_pos},
            },
        )

    # Стандартные ошибки валидации (отсутствует поле, неверный тип и т.п.)
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Перехватывает все необработанные исключения.

    Стек трейс пишется в лог для диагностики, клиенту возвращается
    только общее сообщение — чтобы не раскрывать внутреннее устройство.
    """
    logger.exception("unhandled_exception", path=str(request.url.path), error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "Внутренняя ошибка сервиса. Попробуйте позже.",
            "details": {},
        },
    )
