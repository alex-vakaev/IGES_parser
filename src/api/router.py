import time

from fastapi import APIRouter, HTTPException, Request, Response

from src.api.schemas import ErrorResponse, ParseRequest, ParseResponse, RenderRequest
from src.core.logging import get_logger
from src.parser.entity_dispatcher import EntityDispatcher
from src.parser.global_parser import GlobalParser
from src.parser.directory_parser import DirectoryParser
from src.parser.iges_reader import IgesReader, IgesFormatError
from src.parser.normalizer import build_normalized_layer
from src.render.renderer import render_iges_image

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


@router.post(
    "/render",
    responses={
        200: {"content": {"image/png": {}, "image/jpeg": {}, "image/svg+xml": {}}},
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    tags=["render"],
)
async def render_iges(body: RenderRequest, request: Request) -> Response:
    """Рендерит IGES в PNG/JPG/SVG.

    Возвращает бинарное тело изображения и служебные X-Render-* заголовки.
    """
    content = body.content
    if not content or not content.strip():
        raise HTTPException(
            status_code=400,
            detail={"error_code": "EMPTY_INPUT", "message": "Поле 'content' не должно быть пустым.", "details": {}},
        )

    start = time.perf_counter()
    try:
        sections = IgesReader().split_sections(content)
        metadata = GlobalParser().parse(sections.global_lines)
        directory = DirectoryParser().parse(sections.directory_lines)
        geometry, dimensions, annotations, _unsupported = EntityDispatcher().dispatch(sections.parameter_lines, directory)

        image_bytes, mime, headers = render_iges_image(
            geometry=geometry,
            annotations=annotations,
            output_format=body.format,
            width_px=body.width_px,
            height_px=body.height_px,
            dpi=body.dpi,
            svg_mode=body.svg_mode,
        )
    except IgesFormatError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "INVALID_FORMAT", "message": str(exc), "details": {}},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error_code": "INVALID_RENDER_OPTIONS", "message": str(exc), "details": {}},
        )
    except Exception as exc:
        logger.error("render_error", error=str(exc))
        raise HTTPException(
            status_code=422,
            detail={"error_code": "RENDER_ERROR", "message": f"Ошибка рендера: {exc}", "details": {}},
        )

    elapsed_ms = round((time.perf_counter() - start) * 1000)
    response_headers = {
        "Content-Disposition": f'inline; filename="drawing.{body.format}"',
        "X-Render-Format": body.format,
        "X-Render-Size-Bytes": str(len(image_bytes)),
        **headers,
    }
    logger.info(
        "render_completed",
        format=body.format,
        output_bytes=len(image_bytes),
        processing_time_ms=elapsed_ms,
        warning_code=headers.get("X-Render-Warning"),
    )
    return Response(content=image_bytes, media_type=mime, headers=response_headers)
