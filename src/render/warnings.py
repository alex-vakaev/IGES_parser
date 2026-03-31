from src.api.schemas import GeometricEntity


def classify_render_warning(geometry: list[GeometricEntity]) -> tuple[str, str] | None:
    """Возвращает предупреждение для пустого/почти пустого рендера.

    Логика простая и прозрачная: если геометрии нет — empty,
    если геометрии очень мало — near_empty.
    """
    if not geometry:
        return "empty", "no_renderable_geometry"
    if len(geometry) < 3:
        return "near_empty", "very_low_visible_primitives"
    return None

