"""Парсеры геометрических сущностей IGES.

Каждая функция принимает список параметров из P-секции (строки через запятую)
и возвращает словарь coordinates для поля GeometricEntity.coordinates.
Первый параметр в списке — всегда entity_type, далее тип-специфичные данные.
"""


def _f(params: list[str], idx: int) -> float:
    """Безопасное извлечение float из списка параметров."""
    try:
        return float(params[idx].strip())
    except (IndexError, ValueError):
        return 0.0


def _i(params: list[str], idx: int) -> int:
    """Безопасное извлечение int из списка параметров."""
    try:
        return int(float(params[idx].strip()))
    except (IndexError, ValueError):
        return 0


def parse_type_100(params: list[str]) -> dict:
    """Type 100 — Circular Arc (дуга окружности).

    Используется для изображения отверстий, скруглений, фасок в виде дуг.
    Параметры: ZT, X1, Y1, X2, Y2, X3, Y3
    ZT — Z-координата плоскости дуги (для 2D чертежей обычно 0).
    (X1, Y1) — центр. (X2, Y2) — начало дуги. (X3, Y3) — конец дуги.
    """
    return {
        "plane_z": _f(params, 1),
        "center": {"x": _f(params, 2), "y": _f(params, 3)},
        "start": {"x": _f(params, 4), "y": _f(params, 5)},
        "end": {"x": _f(params, 6), "y": _f(params, 7)},
    }


def parse_type_102(params: list[str]) -> dict:
    """Type 102 — Composite Curve (составная кривая).

    Объединяет несколько кривых в одну цепочку — используется для
    обозначения сложных контуров деталей (например, профиль зуба шестерни).
    Параметры: N, DE1, DE2, ..., DEN  (N — число компонент, DE — указатели)
    """
    n = _i(params, 1)
    component_seq_nums = [_i(params, 2 + k) for k in range(n)]
    return {"component_count": n, "component_sequence_numbers": component_seq_nums}


def parse_type_104(params: list[str]) -> dict:
    """Type 104 — Conic Arc (коническое сечение: эллипс, парабола, гипербола).

    Используется для изображения эллиптических контуров деталей.
    Параметры: A, B, C, D, E, F, ZT, X1, Y1, X2, Y2
    Уравнение: A*x² + B*x*y + C*y² + D*x + E*y + F = 0
    """
    return {
        "a": _f(params, 1), "b": _f(params, 2), "c": _f(params, 3),
        "d": _f(params, 4), "e": _f(params, 5), "f": _f(params, 6),
        "z_plane": _f(params, 7),
        "start": {"x": _f(params, 8), "y": _f(params, 9)},
        "end": {"x": _f(params, 10), "y": _f(params, 11)},
    }


def parse_type_106(params: list[str]) -> dict:
    """Type 106 — Copious Data (набор точек или полилиний).

    IP=1: 2D-пары (X,Y) с общим смещением ZT — witness lines, выноски.
          Параметры: IP, N, ZT, X1, Y1, X2, Y2, ...
    IP=2: 3D-тройки (X,Y,Z).
          Параметры: IP, N, X1, Y1, Z1, ...
    IP=3: секстеты (X,Y,Z,I,J,K) — точки с векторами нормалей.
          Параметры: IP, N, X1, Y1, Z1, I1, J1, K1, ...
    """
    ip = _i(params, 1)
    n = _i(params, 2)
    points = []

    if ip == 1:
        # 2D (X,Y) пары; params[3] = ZT (общая Z), данные начинаются с params[4]
        zt = _f(params, 3)
        for k in range(n):
            base = 4 + k * 2
            points.append({"x": _f(params, base), "y": _f(params, base + 1)})
        return {"form": ip, "common_z": zt, "points": points}

    if ip == 2:
        # 3D (X,Y,Z) тройки, данные начинаются с params[3]
        for k in range(n):
            base = 3 + k * 3
            points.append({"x": _f(params, base), "y": _f(params, base + 1), "z": _f(params, base + 2)})
        return {"form": ip, "points": points}

    # IP=3: секстеты — берём координаты точки, вектор нормали опускаем
    for k in range(n):
        base = 3 + k * 6
        points.append({"x": _f(params, base), "y": _f(params, base + 1), "z": _f(params, base + 2)})
    return {"form": ip, "points": points}


def parse_type_110(params: list[str]) -> dict:
    """Type 110 — Line (отрезок прямой).

    Основной примитив 2D-чертежа. Образует контуры деталей, осевые линии,
    линии разреза и прочие элементы оформления по ГОСТ.
    Параметры: X1, Y1, Z1, X2, Y2, Z2
    """
    return {
        "start": {"x": _f(params, 1), "y": _f(params, 2), "z": _f(params, 3)},
        "end":   {"x": _f(params, 4), "y": _f(params, 5), "z": _f(params, 6)},
    }


def parse_type_116(params: list[str]) -> dict:
    """Type 116 — Point (точка).

    Обозначает характерную точку на чертеже: центр отверстия,
    точку привязки размера, начало координат вида.
    Параметры: X, Y, Z
    """
    return {"x": _f(params, 1), "y": _f(params, 2), "z": _f(params, 3)}


def parse_type_126(params: list[str]) -> dict:
    """Type 126 — Rational B-Spline Curve (NURBS-кривая).

    Используется для плавных контуров: лекальные кривые, профили кулачков,
    сплайны. Содержит узловой вектор и управляющие точки.
    Параметры: K, M, PROP1..4, knots[], weights[], control_points[]
    """
    k = _i(params, 1)  # K: число управляющих точек = K+1
    m = _i(params, 2)  # M: степень кривой
    # Пропускаем PROP1-4 (params 3-6), затем узловой вектор (k+m+2 значений)
    knot_count = k + m + 2
    knot_start = 7
    weight_start = knot_start + knot_count
    cp_start = weight_start + (k + 1)
    control_points = []
    for j in range(k + 1):
        base = cp_start + j * 3
        control_points.append({
            "x": _f(params, base),
            "y": _f(params, base + 1),
            "z": _f(params, base + 2),
        })
    return {"degree": m, "knot_count": knot_count, "control_points": control_points}


def parse_type_230(params: list[str]) -> dict:
    """Type 230 — Sectioned Area (штриховка сечения).

    Обозначает заштрихованную область на чертеже (разрез, сечение).
    Бизнес-значение: LLM может по наличию штриховки определить вид разреза.
    Параметры: DE_ptr (граница), pattern, angle, ...
    """
    return {
        "boundary_sequence_number": _i(params, 1),
        "hatch_pattern": _i(params, 2),
        "hatch_angle": _f(params, 3),
    }


def parse_type_314(params: list[str]) -> dict:
    """Type 314 — Color Definition Entity (определение цвета).

    Задаёт цвет через RGB-компоненты в диапазоне 0-100 (не 0-255).
    Используется другими сущностями через поле color в Directory Entry.
    Параметры: R, G, B [, color_name]
    """
    return {
        "r": _f(params, 1),
        "g": _f(params, 2),
        "b": _f(params, 3),
    }


def parse_type_402(params: list[str]) -> dict:
    """Type 402 — Associativity Instance (группа сущностей).

    Объединяет произвольный набор сущностей в именованную группу.
    Форма (form number из DE) определяет тип группировки:
    Form 1/7: неупорядоченная/упорядоченная группа, Form 9: вид и т.д.
    Параметры: N, DE1, DE2, ..., DEN
    """
    n = _i(params, 1)
    members = [_i(params, 2 + k) for k in range(n)]
    return {"member_count": n, "member_sequence_numbers": members}


# Маппинг типа сущности на имя и функцию-парсер
GEOMETRY_PARSERS: dict[int, tuple[str, callable]] = {
    100: ("circular_arc", parse_type_100),
    102: ("composite_curve", parse_type_102),
    104: ("conic_arc", parse_type_104),
    106: ("copious_data", parse_type_106),
    110: ("line", parse_type_110),
    116: ("point", parse_type_116),
    126: ("b_spline_curve", parse_type_126),
    230: ("sectioned_area", parse_type_230),
    314: ("color_definition", parse_type_314),
    402: ("associativity_group", parse_type_402),
}
