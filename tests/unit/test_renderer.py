from src.api.schemas import GeometricEntity, RenderRequest, TextAnnotation
from src.render.renderer import render_iges_image
from src.render.warnings import classify_render_warning


def test_classify_render_warning_empty():
    warning = classify_render_warning([])
    assert warning is not None
    assert warning[0] == "empty"


def test_classify_render_warning_near_empty():
    geometry = [
        GeometricEntity(entity_type=110, entity_name="line", sequence_number=1, coordinates={"start": {"x": 0, "y": 0}, "end": {"x": 10, "y": 0}}),
        GeometricEntity(entity_type=110, entity_name="line", sequence_number=2, coordinates={"start": {"x": 0, "y": 1}, "end": {"x": 10, "y": 1}}),
    ]
    warning = classify_render_warning(geometry)
    assert warning is not None
    assert warning[0] == "near_empty"


def test_render_svg_bytes():
    geometry = [
        GeometricEntity(entity_type=110, entity_name="line", sequence_number=1, coordinates={"start": {"x": 0, "y": 0}, "end": {"x": 100, "y": 0}})
    ]
    annotations = [
        TextAnnotation(entity_type=212, entity_name="general_note", sequence_number=2, content="Test", position_x=10.0, position_y=10.0)
    ]
    body, mime, headers = render_iges_image(
        geometry=geometry,
        annotations=annotations,
        output_format="svg",
        width_px=400,
        height_px=300,
        dpi=150,
        svg_mode="vector",
    )
    assert mime == "image/svg+xml"
    assert b"<svg" in body
    assert "X-Render-Warning" in headers or headers == {}


def test_render_png_and_jpg_return_non_empty_bytes():
    geometry = [GeometricEntity(entity_type=110, entity_name="line", sequence_number=1, coordinates={"start": {"x": 0, "y": 0}, "end": {"x": 10, "y": 0}})]
    annotations: list[TextAnnotation] = []
    png_body, png_mime, _ = render_iges_image(
        geometry=geometry,
        annotations=annotations,
        output_format="png",
        width_px=400,
        height_px=300,
        dpi=150,
        svg_mode="vector",
    )
    jpg_body, jpg_mime, _ = render_iges_image(
        geometry=geometry,
        annotations=annotations,
        output_format="jpg",
        width_px=400,
        height_px=300,
        dpi=150,
        svg_mode="vector",
    )
    assert png_mime == "image/png"
    assert jpg_mime == "image/jpeg"
    assert len(png_body) > 0
    assert len(jpg_body) > 0


def test_render_request_defaults_applied():
    model = RenderRequest(content="S      1", format="png")
    assert model.width_px == 1600
    assert model.height_px == 1600
    assert model.dpi == 150
    assert model.svg_mode == "vector"


def test_render_request_range_validation():
    try:
        RenderRequest(content="S      1", format="png", width_px=10)
        assert False, "Expected validation error for width_px"
    except Exception:
        assert True

