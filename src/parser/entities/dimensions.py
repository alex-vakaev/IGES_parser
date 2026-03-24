"""Парсеры размерных аннотаций IGES.

Размерные сущности описывают числовые параметры детали: длины, углы, радиусы.
Каждая содержит ссылку на General Note (Type 212) с текстовым представлением
размера «как на чертеже» и координаты стрелок привязки.
"""


def _f(params: list[str], idx: int) -> float:
    try:
        return float(params[idx].strip())
    except (IndexError, ValueError):
        return 0.0


def _i(params: list[str], idx: int) -> int:
    try:
        return int(float(params[idx].strip()))
    except (IndexError, ValueError):
        return 0


def _arrow_coords(params: list[str], start_idx: int, count: int = 2) -> list[dict]:
    """Извлекает координаты стрелок размерной линии."""
    coords = []
    for k in range(count):
        base = start_idx + k * 2
        coords.append({"x": _f(params, base), "y": _f(params, base + 1)})
    return coords


def parse_type_202(params: list[str]) -> dict:
    """Type 202 — Angular Dimension (угловой размер).

    Обозначает угол между двумя линиями или плоскостями детали.
    Используется для указания углов скосов, конусности, расположения элементов.
    Параметры: NOTE_DE, ARC_DE, X1, Y1, X2, Y2, X3, Y3 (координаты дуги)
    """
    return {
        "note_seq": _i(params, 1),    # ссылка на General Note с текстом угла
        "arc_seq": _i(params, 2),     # ссылка на дугу размерной линии
        "arrow_coordinates": _arrow_coords(params, 3, 3),
    }


def parse_type_206(params: list[str]) -> dict:
    """Type 206 — Diameter Dimension (размер диаметра).

    Обозначает диаметр цилиндрического элемента (отверстие, вал, бобышка).
    Критически важен для паспорта детали: основной параметр тел вращения.
    Параметры: NOTE_DE, X1, Y1, X2, Y2
    """
    return {
        "note_seq": _i(params, 1),
        "arrow_coordinates": _arrow_coords(params, 2, 2),
    }


def parse_type_216(params: list[str]) -> dict:
    """Type 216 — Linear Dimension (линейный размер).

    Основной тип размера на чертеже: длина, ширина, высота элемента.
    Именно линейные размеры формируют габаритные характеристики детали.
    Параметры: NOTE_DE, X1, Y1, X2, Y2
    """
    return {
        "note_seq": _i(params, 1),
        "arrow_coordinates": _arrow_coords(params, 2, 2),
    }


def parse_type_218(params: list[str]) -> dict:
    """Type 218 — Ordinate Dimension (ординатный размер).

    Размер от общей базы (ординаты). Применяется для цепочек размеров
    от одной нулевой точки — характерно для деталей с несколькими отверстиями.
    Параметры: NOTE_DE, X1, Y1
    """
    return {
        "note_seq": _i(params, 1),
        "arrow_coordinates": [{"x": _f(params, 2), "y": _f(params, 3)}],
    }


def parse_type_222(params: list[str]) -> dict:
    """Type 222 — Radius Dimension (размер радиуса).

    Обозначает радиус скругления или дуги. Вместе с Type 206 (диаметр)
    образует полное описание круглых и скруглённых элементов детали.
    Параметры: NOTE_DE, X1, Y1
    """
    return {
        "note_seq": _i(params, 1),
        "arrow_coordinates": [{"x": _f(params, 2), "y": _f(params, 3)}],
    }


# Маппинг: entity_type → (dimension_type, функция-парсер)
DIMENSION_PARSERS: dict[int, tuple[str, callable]] = {
    202: ("angular", parse_type_202),
    206: ("diameter", parse_type_206),
    216: ("linear", parse_type_216),
    218: ("ordinate", parse_type_218),
    222: ("radius", parse_type_222),
}
