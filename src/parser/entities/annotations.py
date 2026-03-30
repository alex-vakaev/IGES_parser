"""Парсеры текстовых аннотаций IGES.

Аннотации — основной источник инженерных данных для паспорта детали:
  Type 212 (General Note): шероховатость (Ra 3.2), допуски (H14/h9),
    марка материала, технические требования, надписи в рамке.
  Type 210 (General Label): метки с выноской (обозначение позиций, видов).
  Type 214 (Leader/Arrow): стрелки, связывающие аннотации с геометрией.
"""

import re


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


def _decode_hollerith(value: str) -> str:
    """Декодирует Hollerith-строку NHtext → text.

    Пример: '6HRa 3.2' → 'Ra 3.2'
    Кириллица сохраняется как есть — строка уже UTF-8 от клиента.
    """
    m = re.match(r"^(\d+)H(.*)$", value.strip(), re.DOTALL)
    if m:
        length = int(m.group(1))
        return m.group(2)[:length]
    return value.strip()


def parse_type_212(params: list[str]) -> dict:
    """Type 212 — General Note (текстовое примечание).

    Самый важный аннотационный тип для паспорта детали.
    Содержит произвольный текст: шероховатость поверхностей (Ra, Rz),
    квалитеты и посадки (H7, h6), технические требования,
    надписи основной надписи (штамп), марку материала.

    Один General Note может содержать несколько текстовых блоков (STRING).
    Параметры: NS (число строк), W1, H1, FC1, SLC1, ANG1, XS1, YS1, ZS1, STR1, ...
    """
    ns = _i(params, 1)  # число текстовых блоков (STRING) в этом Note
    texts: list[str] = []
    positions: list[dict] = []
    char_heights: list[float] = []

    # IGES 212 на практике встречается в нескольких раскладках параметров.
    #
    # 1) "Классический" (часто в минимальных фикстурах):
    #    212, NS, W, H, FC, SLC, ANG, XS, YS, ZS, MIRROR, ROT, STR, ...
    #    -> 9-11 числовых параметров + 1 Hollerith-строка на один STRING.
    #
    # 2) Экспорт C3D Converter / KOMPAS (видно на реальных файлах):
    #    212, NS, W, H, FC, SLC, ANG, XS, YS, ZS, X, Y, Z, STR, ...
    #    -> 11 числовых параметров + 1 Hollerith-строка на один STRING.
    #
    # Мы авто-детектим шаг по общему числу параметров.
    # step=12: 11 числовых + STR
    # step=10:  9 числовых + STR (legacy-файлы)
    step = 12 if len(params) >= 2 + ns * 12 else 10
    for k in range(ns):
        base = 2 + k * step
        char_height = _f(params, base + 1)

        if step == 12:
            # KOMPAS/C3D: ... XS,YS,ZS,X,Y,Z,STR
            x = _f(params, base + 8)
            y = _f(params, base + 9)
            text_idx = base + 11
        else:
            # Legacy: ... XS,YS,ZS,MIRROR,ROT,STR
            x = _f(params, base + 5)
            y = _f(params, base + 6)
            text_idx = base + 9

        raw_text = params[text_idx].strip() if text_idx < len(params) else ""
        texts.append(_decode_hollerith(raw_text))
        positions.append({"x": x, "y": y})
        char_heights.append(char_height)

    # Объединяем все строки в одну, как инженер читает блок текста
    combined_text = " ".join(t for t in texts if t)

    return {
        "content": combined_text,
        "position_x": positions[0]["x"] if positions else 0.0,
        "position_y": positions[0]["y"] if positions else 0.0,
        "char_height": char_heights[0] if char_heights else None,
    }


def parse_type_210(params: list[str]) -> dict:
    """Type 210 — General Label (метка с выноской).

    Метка с текстом и стрелкой-указателем. Применяется для обозначения
    видов, сечений, выносных элементов, позиций на сборочных чертежах.
    Параметры: NOTE_DE, NARR, ...leader data...
    """
    return {
        "note_seq": _i(params, 1),    # ссылка на связанный General Note
        "arrow_count": _i(params, 2),
        "content": "",  # текст находится в linked Note, заполняется dispatcher-ом
        "position_x": None,
        "position_y": None,
        "char_height": None,
    }


def parse_type_214(params: list[str]) -> dict:
    """Type 214 — Leader (Arrow) (стрелка-выноска).

    Стрелка соединяет текстовую аннотацию с геометрическим объектом.
    Используется в размерах и примечаниях. Позиции стрелок нужны
    для понимания, к каким элементам относится аннотация.
    Параметры: NARR (форма стрелки), ZT, XH, YH, (сегменты)
    """
    arrow_form = _i(params, 1)
    x_head = _f(params, 3)
    y_head = _f(params, 4)
    return {
        "arrow_form": arrow_form,
        "head": {"x": x_head, "y": y_head},
        "content": "",
        "position_x": x_head,
        "position_y": y_head,
        "char_height": None,
    }


# Маппинг: entity_type → (entity_name, функция-парсер)
ANNOTATION_PARSERS: dict[int, tuple[str, callable]] = {
    210: ("general_label", parse_type_210),
    212: ("general_note", parse_type_212),
    214: ("leader_arrow", parse_type_214),
}
