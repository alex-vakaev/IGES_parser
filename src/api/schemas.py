from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator

from src.core.config import settings


# ---------------------------------------------------------------------------
# Запрос
# ---------------------------------------------------------------------------

class ParseRequest(BaseModel):
    """Тело POST /parse.

    Клиент передаёт полное текстовое содержимое IGES-файла в поле content.
    Валидация пустого content выполняется в роутере (HTTP 400 EMPTY_INPUT),
    а не здесь — чтобы клиент получил бизнес-ошибку, а не технический 422.
    """

    content: str


class RenderRequest(BaseModel):
    """Тело POST /render."""

    content: str
    format: Literal["png", "jpg", "svg"]
    width_px: int = settings.render_default_width_px
    height_px: int = settings.render_default_height_px
    dpi: int = settings.render_default_dpi
    svg_mode: Literal["vector", "raster_embedded"] = "vector"

    @field_validator("width_px")
    @classmethod
    def validate_width(cls, value: int) -> int:
        if not (settings.render_min_side_px <= value <= settings.render_max_side_px):
            raise ValueError(f"width_px must be in range {settings.render_min_side_px}..{settings.render_max_side_px}")
        return value

    @field_validator("height_px")
    @classmethod
    def validate_height(cls, value: int) -> int:
        if not (settings.render_min_side_px <= value <= settings.render_max_side_px):
            raise ValueError(f"height_px must be in range {settings.render_min_side_px}..{settings.render_max_side_px}")
        return value

    @field_validator("dpi")
    @classmethod
    def validate_dpi(cls, value: int) -> int:
        if not (settings.render_min_dpi <= value <= settings.render_max_dpi):
            raise ValueError(f"dpi must be in range {settings.render_min_dpi}..{settings.render_max_dpi}")
        return value


# ---------------------------------------------------------------------------
# Координаты и bounding box
# ---------------------------------------------------------------------------

class BoundingBox(BaseModel):
    """Габариты чертёжного поля по всем геометрическим сущностям."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float


# ---------------------------------------------------------------------------
# Метаданные чертежа
# ---------------------------------------------------------------------------

class DrawingMetadata(BaseModel):
    """Метаданные из Global-секции IGES-файла.

    Содержит служебную информацию о чертеже: кто создал, в каких единицах,
    по какому стандарту. Нужна LLM для контекстуализации данных детали.
    """

    author: str | None = None
    organization: str | None = None
    created_at: str | None = None
    modified_at: str | None = None
    drawing_title: str | None = None
    unit: str = "unknown"
    unit_code: int | None = None
    scale: float | None = None
    iges_version: str | None = None
    drafting_standard: str | None = None


# ---------------------------------------------------------------------------
# Геометрические сущности
# ---------------------------------------------------------------------------

class GeometricEntity(BaseModel):
    """Один геометрический примитив из P-секции IGES.

    Содержит тип, атрибуты оформления и тип-специфичные координаты.
    raw_parameters хранят исходные строки из P-секции для полноты вывода.
    """

    entity_type: int
    entity_name: str
    sequence_number: int
    layer: int | None = None
    color: int | None = None
    line_weight: int | None = None
    coordinates: dict = {}
    raw_parameters: list[str] = []


# ---------------------------------------------------------------------------
# Размерные аннотации
# ---------------------------------------------------------------------------

class DimensionAnnotation(BaseModel):
    """Размерная аннотация на чертеже (линейный, угловой, радиусный и т.д.).

    Числовое value — основной размер детали. text_display — строка «как на чертеже»,
    которую LLM должна воспринимать так же, как инженер читает размер на бумаге.
    """

    entity_type: int
    dimension_type: str  # linear | angular | radial | diameter | ordinate
    sequence_number: int
    value: float | None = None
    unit: str | None = None
    text_display: str | None = None
    arrow_coordinates: list[dict] | None = None
    raw_parameters: list[str] = []


# ---------------------------------------------------------------------------
# Текстовые аннотации
# ---------------------------------------------------------------------------

class TextAnnotation(BaseModel):
    """Текстовое примечание или метка на чертеже.

    Именно здесь хранятся шероховатость (Ra 3.2), допуски (H14),
    марка материала и прочие текстовые данные по ГОСТ.
    LLM читает эти строки для составления паспорта детали.
    """

    entity_type: int
    entity_name: str  # general_note | general_label
    sequence_number: int
    content: str
    position_x: float | None = None
    position_y: float | None = None
    char_height: float | None = None
    raw_parameters: list[str] = []


# ---------------------------------------------------------------------------
# Сводка
# ---------------------------------------------------------------------------

class DrawingSummary(BaseModel):
    """Предрассчитанная сводка по всему чертежу.

    Позволяет LLM сразу прочитать габариты и состав чертежа без обхода
    всех геометрических списков. Снижает нагрузку на токены.
    """

    bounding_box: BoundingBox | None = None
    entity_counts: dict[str, int] = {}
    total_entities: int = 0
    units: str = "unknown"


# ---------------------------------------------------------------------------
# Нераспознанные сущности
# ---------------------------------------------------------------------------

class UnsupportedEntityRecord(BaseModel):
    """Тип сущности IGES, не поддерживаемый текущей версией парсера.

    Вместо ошибки записывается в ответ — не ломает парсинг при встрече
    нестандартных или редких типов.
    """

    entity_type: int
    count: int


# ---------------------------------------------------------------------------
# Корневой ответ
# ---------------------------------------------------------------------------

class ParseResponse(BaseModel):
    """Полный структурированный ответ на запрос парсинга IGES-файла."""

    drawing_metadata: DrawingMetadata
    # -----------------------------------------------------------------------
    # Нормализованный слой (Priority 1+2): для формирования паспорта детали.
    # Исходные поля geometry/dimensions/annotations остаются для трассировки.
    # -----------------------------------------------------------------------
    title_block: dict | None = None
    sheet_regions: dict | None = None
    views: list[dict] = []
    features: list[dict] = []
    dimension_objects: list[dict] = []
    annotations_normalized: list[dict] = []
    tables: list[dict] = []
    surface_finish: list[dict] = []
    general_tolerances: dict | None = None
    technical_requirements: list[dict] = []
    datums: list[dict] = []
    gdt: list[dict] = []
    hole_patterns: list[dict] = []
    links: dict | None = None
    resolved_parameters: dict | None = None
    extraction_diagnostics: dict | None = None
    dedup_groups: list[dict] = []
    geometry: list[GeometricEntity] = []
    dimensions: list[DimensionAnnotation] = []
    annotations: list[TextAnnotation] = []
    summary: DrawingSummary
    unsupported_entities: list[UnsupportedEntityRecord] = []


# ---------------------------------------------------------------------------
# Ошибки
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Структурированный ответ при ошибке.

    error_code позволяет downstream-системе (LLM-пайплайну) программно
    реагировать на конкретный тип проблемы.
    """

    error_code: str  # EMPTY_INPUT | INVALID_FORMAT | SIZE_EXCEEDED | PARSE_ERROR | INTERNAL_ERROR
    message: str
    details: dict = {}
