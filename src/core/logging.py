import logging
import sys

import structlog

from src.core.config import settings


def configure_logging() -> None:
    """Настраивает structlog для вывода логов в stdout.

    В production (LOG_FORMAT=json) пишет машиночитаемый JSON — удобно для
    Docker, Kubernetes и систем сбора логов (ELK, Loki).
    В dev (LOG_FORMAT=pretty) пишет цветной текст — удобно при локальной разработке.
    """
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Возвращает именованный structlog-логгер.

    Использование: logger = get_logger(__name__)
    """
    return structlog.get_logger(name)
