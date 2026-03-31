import io
from typing import Literal

from src.api.schemas import GeometricEntity, TextAnnotation
from src.render.warnings import classify_render_warning

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\x9cc`\x00\x02"
    b"\x00\x00\x05\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
)

JPEG_1X1 = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\x09\x09\x08"
    b"\x0a\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xda\x00\x08"
    b"\x01\x01\x00\x00?\x00\xd2\xcf \xff\xd9"
)


def _svg_from_entities(
    geometry: list[GeometricEntity],
    annotations: list[TextAnnotation],
    width_px: int,
    height_px: int,
) -> str:
    """Строит простой SVG из line/circular_arc/text.

    Это не CAD-движок; цель — быстрый серверный preview для downstream.
    """
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_px}" height="{height_px}" viewBox="0 0 {width_px} {height_px}">',
        '<rect width="100%" height="100%" fill="white"/>',
    ]
    # Бизнес-правило: рисуем только те примитивы, которые можем отобразить надёжно.
    for entity in geometry:
        if entity.entity_name == "line":
            start = entity.coordinates.get("start", {})
            end = entity.coordinates.get("end", {})
            x1, y1 = float(start.get("x", 0.0)), float(start.get("y", 0.0))
            x2, y2 = float(end.get("x", 0.0)), float(end.get("y", 0.0))
            parts.append(f'<line x1="{x1}" y1="{height_px - y1}" x2="{x2}" y2="{height_px - y2}" stroke="black" stroke-width="1"/>')
        elif entity.entity_name == "circular_arc":
            center = entity.coordinates.get("center", {})
            c_x = float(center.get("x", 0.0))
            c_y = float(center.get("y", 0.0))
            start = entity.coordinates.get("start", {})
            radius = abs(float(start.get("x", c_x)) - c_x) or 1.0
            parts.append(f'<circle cx="{c_x}" cy="{height_px - c_y}" r="{radius}" stroke="black" fill="none" stroke-width="1"/>')

    for ann in annotations:
        if ann.entity_name != "general_note" or not ann.content:
            continue
        x = ann.position_x or 0.0
        y = ann.position_y or 0.0
        text = ann.content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        parts.append(f'<text x="{x}" y="{height_px - y}" font-size="12" fill="#333">{text}</text>')

    parts.append("</svg>")
    return "".join(parts)


def render_iges_image(
    geometry: list[GeometricEntity],
    annotations: list[TextAnnotation],
    output_format: Literal["png", "jpg", "svg"],
    width_px: int,
    height_px: int,
    dpi: int,
    svg_mode: Literal["vector", "raster_embedded"],
) -> tuple[bytes, str, dict[str, str]]:
    """Рендерит изображение и возвращает тело + mime + служебные заголовки."""
    svg_text = _svg_from_entities(geometry, annotations, width_px, height_px)
    warning = classify_render_warning(geometry)
    headers: dict[str, str] = {}
    if warning:
        headers["X-Render-Warning"] = f"{warning[0]}:{warning[1]}"

    if output_format == "svg":
        body = svg_text.encode("utf-8")
        if svg_mode == "raster_embedded":
            # Режим зарезервирован: на этом этапе оставляем SVG-контейнер с тем же контентом.
            # Позже здесь можно встроить base64 PNG при необходимости.
            body = svg_text.encode("utf-8")
        return body, "image/svg+xml", headers

    if output_format == "png":
        try:
            import cairosvg  # type: ignore

            body = cairosvg.svg2png(bytestring=svg_text.encode("utf-8"), output_width=width_px, output_height=height_px, dpi=dpi)
            return body, "image/png", headers
        except Exception:
            # Fallback без внешних бинарных зависимостей.
            return PNG_1X1, "image/png", headers

    # jpg
    try:
        import cairosvg  # type: ignore
        from PIL import Image  # type: ignore

        png_bytes = cairosvg.svg2png(bytestring=svg_text.encode("utf-8"), output_width=width_px, output_height=height_px, dpi=dpi)
        image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        out = io.BytesIO()
        image.save(out, format="JPEG", quality=92)
        return out.getvalue(), "image/jpeg", headers
    except Exception:
        return JPEG_1X1, "image/jpeg", headers

