"""T028 + T035 — Unit-тесты для парсеров сущностей и EntityDispatcher."""

import pytest

from src.parser.entities.geometry import parse_type_100, parse_type_110, parse_type_116
from src.parser.entities.dimensions import parse_type_216, parse_type_222
from src.parser.entities.annotations import parse_type_212, _decode_hollerith
from src.parser.entity_dispatcher import EntityDispatcher
from src.api.schemas import DrawingMetadata


# --- Geometry parsers ---

def test_parse_line_type_110():
    """Type 110: координаты start/end корректно извлекаются."""
    params = ["110", "1.0", "2.0", "0.0", "10.0", "5.0", "0.0"]
    result = parse_type_110(params)
    assert result["start"] == {"x": 1.0, "y": 2.0, "z": 0.0}
    assert result["end"] == {"x": 10.0, "y": 5.0, "z": 0.0}


def test_parse_circular_arc_type_100():
    """Type 100: центр и начало/конец дуги корректно извлекаются."""
    params = ["100", "0.0", "5.0", "5.0", "10.0", "5.0", "0.0", "5.0"]
    result = parse_type_100(params)
    assert result["center"] == {"x": 5.0, "y": 5.0}
    assert result["start"]["x"] == 10.0


def test_parse_point_type_116():
    """Type 116: x, y, z корректно извлекаются."""
    params = ["116", "3.0", "7.0", "0.0"]
    result = parse_type_116(params)
    assert result == {"x": 3.0, "y": 7.0, "z": 0.0}


def test_parse_type_116_missing_params():
    """Type 116 с отсутствующими параметрами → 0.0 по умолчанию."""
    params = ["116"]
    result = parse_type_116(params)
    assert result["x"] == 0.0


# --- Dimension parsers ---

def test_parse_linear_dimension_type_216():
    """Type 216: стрелки извлекаются корректно."""
    params = ["216", "3", "0.0", "-5.0", "100.0", "-5.0"]
    result = parse_type_216(params)
    assert result["note_seq"] == 3
    assert len(result["arrow_coordinates"]) == 2


def test_parse_radius_dimension_type_222():
    """Type 222: одна стрелка и note_seq."""
    params = ["222", "5", "25.0", "0.0"]
    result = parse_type_222(params)
    assert result["note_seq"] == 5
    assert result["arrow_coordinates"][0] == {"x": 25.0, "y": 0.0}


# --- Annotation parsers ---

def test_decode_hollerith_simple():
    """Hollerith 6HRa 3.2 → 'Ra 3.2'."""
    assert _decode_hollerith("6HRa 3.2") == "Ra 3.2"


def test_decode_hollerith_cyrillic():
    """Hollerith с кириллицей корректно декодируется — 6 символов."""
    assert _decode_hollerith("6HДеталь") == "Деталь"


def test_decode_hollerith_plain_string():
    """Не-Hollerith строка возвращается как есть."""
    assert _decode_hollerith("plain") == "plain"


def test_parse_general_note_type_212():
    """Type 212: контент декодируется из Hollerith."""
    # Параметры: NS=1, W=3.5, H=1.0, FC=0, SLC=0.0, ANG=0.0, XS=0.0, YS=0.0, ZS=0.0, MIRROR=0, ROT=0.0, STR
    params = ["212", "1", "3.5", "1.0", "0", "0.0", "0.0", "0.0", "0.0", "0", "0.0", "6HRa 3.2"]
    result = parse_type_212(params)
    assert result["content"] == "Ra 3.2"
    assert result["position_x"] == 0.0


# --- EntityDispatcher ---

def test_compute_summary_counts_entities():
    """compute_summary правильно считает сущности."""
    from src.api.schemas import GeometricEntity, DimensionAnnotation, TextAnnotation

    geo = [GeometricEntity(entity_type=110, entity_name="line", sequence_number=1)]
    dims = [DimensionAnnotation(entity_type=216, dimension_type="linear", sequence_number=3)]
    anns = [TextAnnotation(entity_type=212, entity_name="general_note", sequence_number=5, content="Ra 3.2")]
    meta = DrawingMetadata()

    dispatcher = EntityDispatcher()
    summary = dispatcher.compute_summary(geo, dims, anns, meta)

    assert summary.total_entities == 3
    assert summary.entity_counts.get("line") == 1
    assert summary.entity_counts.get("linear_dimension") == 1
    assert summary.entity_counts.get("general_note") == 1


def test_compute_summary_bounding_box():
    """bounding_box корректно вычисляется по координатам линии."""
    from src.api.schemas import GeometricEntity

    geo = [GeometricEntity(
        entity_type=110,
        entity_name="line",
        sequence_number=1,
        coordinates={"start": {"x": 0.0, "y": 0.0, "z": 0.0}, "end": {"x": 100.0, "y": 50.0, "z": 0.0}},
    )]
    meta = DrawingMetadata()
    dispatcher = EntityDispatcher()
    summary = dispatcher.compute_summary(geo, [], [], meta)

    assert summary.bounding_box is not None
    assert summary.bounding_box.min_x == 0.0
    assert summary.bounding_box.max_x == 100.0
    assert summary.bounding_box.max_y == 50.0


def test_compute_summary_empty_geometry_has_no_bbox():
    """При отсутствии геометрии bounding_box = None."""
    meta = DrawingMetadata()
    dispatcher = EntityDispatcher()
    summary = dispatcher.compute_summary([], [], [], meta)
    assert summary.bounding_box is None


# ---------------------------------------------------------------------------
# T035: Edge-case тесты compute_summary (US3)
# ---------------------------------------------------------------------------

def test_compute_summary_multiple_lines_correct_bbox():
    """Bounding box охватывает все точки нескольких линий."""
    from src.api.schemas import GeometricEntity

    geo = [
        GeometricEntity(
            entity_type=110, entity_name="line", sequence_number=1,
            coordinates={"start": {"x": -10.0, "y": 5.0, "z": 0.0}, "end": {"x": 50.0, "y": 20.0, "z": 0.0}},
        ),
        GeometricEntity(
            entity_type=110, entity_name="line", sequence_number=3,
            coordinates={"start": {"x": 0.0, "y": -5.0, "z": 0.0}, "end": {"x": 80.0, "y": 30.0, "z": 0.0}},
        ),
    ]
    meta = DrawingMetadata()
    summary = EntityDispatcher().compute_summary(geo, [], [], meta)

    assert summary.bounding_box is not None
    assert summary.bounding_box.min_x == -10.0
    assert summary.bounding_box.max_x == 80.0
    assert summary.bounding_box.min_y == -5.0
    assert summary.bounding_box.max_y == 30.0


def test_compute_summary_units_from_metadata():
    """summary.units совпадает с metadata.unit."""
    meta = DrawingMetadata(unit="mm", unit_code=2)
    summary = EntityDispatcher().compute_summary([], [], [], meta)
    assert summary.units == "mm"


def test_compute_summary_entity_counts_by_type():
    """entity_counts правильно разделяет геометрию и аннотации по именам."""
    from src.api.schemas import GeometricEntity, TextAnnotation

    geo = [
        GeometricEntity(entity_type=110, entity_name="line", sequence_number=1),
        GeometricEntity(entity_type=110, entity_name="line", sequence_number=3),
        GeometricEntity(entity_type=100, entity_name="circular_arc", sequence_number=5),
    ]
    anns = [
        TextAnnotation(entity_type=212, entity_name="general_note", sequence_number=7, content="Ra 3.2"),
    ]
    meta = DrawingMetadata()
    summary = EntityDispatcher().compute_summary(geo, [], anns, meta)

    assert summary.entity_counts["line"] == 2
    assert summary.entity_counts["circular_arc"] == 1
    assert summary.entity_counts["general_note"] == 1
    assert summary.total_entities == 4


def test_compute_summary_only_annotations_no_bbox():
    """Только аннотации без геометрии → bounding_box = None."""
    from src.api.schemas import TextAnnotation

    anns = [TextAnnotation(entity_type=212, entity_name="general_note", sequence_number=1, content="Rx")]
    meta = DrawingMetadata()
    summary = EntityDispatcher().compute_summary([], [], anns, meta)
    assert summary.bounding_box is None
    assert summary.total_entities == 1
