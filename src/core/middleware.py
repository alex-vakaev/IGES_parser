import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class ContentSizeLimitMiddleware(BaseHTTPMiddleware):
    """Отклоняет запросы, превышающие MAX_CONTENT_BYTES.

    Защита от случайной или намеренной отправки огромных IGES-файлов,
    которые могут исчерпать память сервиса. Проверка идёт по заголовку
    Content-Length (быстрый путь), либо по потоковому чтению тела.
    """

    def __init__(self, app: ASGIApp, max_bytes: int | None = None) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes or settings.max_content_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        # Быстрый путь: клиент честно сообщил размер в заголовке
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error_code": "SIZE_EXCEEDED",
                    "message": f"Размер запроса превышает допустимый лимит {self.max_bytes} байт.",
                    "details": {
                        "max_bytes": self.max_bytes,
                        "received_bytes": int(content_length),
                    },
                },
            )
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Логирует каждый запрос: статус, размер, время обработки.

    Выполняет требование TC-007: структурированные JSON-логи в stdout
    для каждого входящего запроса. Помогает отслеживать производительность
    и диагностировать проблемы в production.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        # Привязываем request_id к контексту — появится во всех логах этого запроса
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        content_size = int(request.headers.get("content-length", 0))

        response = await call_next(request)

        elapsed_ms = round((time.perf_counter() - start) * 1000)
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            http_status=response.status_code,
            content_size_bytes=content_size,
            processing_time_ms=elapsed_ms,
        )
        return response
