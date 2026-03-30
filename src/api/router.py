import time

from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import ErrorResponse, ParseRequest, ParseResponse
from src.core.logging import get_logger
from src.parser.entity_dispatcher import EntityDispatcher
from src.parser.global_parser import GlobalParser
from src.parser.directory_parser import DirectoryParser
from src.parser.iges_reader import IgesReader, IgesFormatError
from src.parser.normalizer import build_normalized_layer

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health", tags=["system"])
async def health() -> dict:
    """Проверка работоспособности сервиса.

    Используется для liveness/readiness probe в Docker и оркестраторах.
    """
    return {"status": "ok"}


@router.post(
    "/parse",
    response_model=ParseResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    tags=["parsing"],
)
async def parse_iges(body: ParseRequest, request: Request) -> ParseResponse:
    """Парсит IGES-файл и возвращает структурированный JSON.

    Принимает текстовое содержимое IGES-файла и последовательно:
    1. Разбивает его на 5 секций (IgesReader)
    2. Извлекает метаданные из Global-секции (GlobalParser)
    3. Строит карту сущностей по Directory Entry (DirectoryParser)
    4. Диспетчеризует Parameter Data по типам сущностей (EntityDispatcher)
    5. Вычисляет сводку: bounding box, счётчики, единицы (compute_summary)

    Бизнес-цель: получить все данные чертежа в виде JSON, пригодного для
    отправки в LLM, которая составит паспорт детали.
    """
    content = body.content

    # Валидация: пустой контент бессмысленен для парсинга
    if not content or not content.strip():
        raise HTTPException(
            status_code=400,
            detail={"error_code": "EMPTY_INPUT", "message": "Поле 'content' не должно быть пустым.", "details": {}},
        )

    start = time.perf_counter()
    try:
        # Шаг 1: разбить IGES-текст на именованные секции
        reader = IgesReader()
        sections = reader.split_sections(content)

        # Шаг 2: извлечь метаданные чертежа из Global-секции
        metadata = GlobalParser().parse(sections.global_lines)

        # Шаг 3: построить карту entity_type → header по Directory Entry
        directory = DirectoryParser().parse(sections.directory_lines)

        # Шаг 4 + 5: диспетчеризовать P-секцию и вычислить сводку
        dispatcher = EntityDispatcher()
        geometry, dimensions, annotations, unsupported = dispatcher.dispatch(
            sections.parameter_lines, directory
        )
        summary = dispatcher.compute_summary(geometry, dimensions, annotations, metadata)

    except IgesFormatError as exc:
        # Файл не является валидным IGES
        logger.warning("invalid_iges_format", reason=str(exc))
        raise HTTPException(
            status_code=422,
            detail={"error_code": "INVALID_FORMAT", "message": str(exc), "details": {}},
        )
    except Exception as exc:
        # Повреждённые данные внутри валидного IGES
        logger.error("parse_error", error=str(exc))
        raise HTTPException(
            status_code=422,
            detail={"error_code": "PARSE_ERROR", "message": f"Ошибка парсинга: {exc}", "details": {}},
        )

    elapsed_ms = round((time.perf_counter() - start) * 1000)
    logger.info(
        "parse_completed",
        entity_count=len(geometry) + len(dimensions) + len(annotations),
        processing_time_ms=elapsed_ms,
    )

    return ParseResponse(
        drawing_metadata=metadata,
        **build_normalized_layer(metadata, dimensions, annotations),
        geometry=geometry,
        dimensions=dimensions,
        annotations=annotations,
        summary=summary,
        unsupported_entities=unsupported,
    )
