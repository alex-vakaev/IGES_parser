import re

from src.api.schemas import DrawingMetadata

# Коды единиц измерения по стандарту IGES 5.3, поле P14
UNIT_MAP: dict[int, str] = {
    1: "inches",
    2: "mm",
    3: "feet",
    4: "miles",
    5: "meters",
    6: "km",
    7: "mils",
    8: "microns",
    9: "cm",
    10: "micro-inches",
}

# Коды стандартов оформления по стандарту IGES 5.3, поле P24
DRAFTING_STANDARD_MAP: dict[int, str] = {
    0: "None",
    1: "ISO",
    2: "AFNOR",
    3: "ANSI",
    4: "BSI",
    5: "CSA",
    6: "DIN",
    7: "JIS",
}


class GlobalParser:
    """Парсит Global-секцию IGES-файла и извлекает метаданные чертежа.

    Global-секция (G) содержит comma-delimited параметры P1-P26.
    Строки объединяются в один текст, затем разбиваются по разделителю
    (по умолчанию запятая, может быть переопределён в P2).

    Бизнес-цель: получить контекст чертежа (автор, организация, единицы,
    стандарт) для корректной интерпретации геометрических данных.
    """

    def parse(self, g_lines: list[str]) -> DrawingMetadata:
        """Разбирает строки G-секции и возвращает DrawingMetadata.

        Каждая строка имеет вид: <72 символа данных><G><7 символов номера>
        Данные объединяются без пробелов, затем парсятся как CSV.
        """
        if not g_lines:
            return DrawingMetadata()

        # Извлекаем только данные (первые 72 символа каждой строки)
        raw = "".join(line[:72].rstrip() for line in g_lines)

        params = self._split_global_params(raw)
        return self._build_metadata(params)

    def _split_global_params(self, raw: str) -> list[str]:
        """Разбивает строку Global-секции по разделителю.

        По стандарту: P1 = разделитель параметров (обычно ','),
        P2 = разделитель записей (обычно ';'). Если не указаны — используем ','.
        Hollerith-строки формата NHtext защищены от ложного разбиения:
        парсим их специально, не разбивая по запятой внутри.
        """
        params: list[str] = []
        current = ""
        i = 0
        while i < len(raw):
            # Hollerith-строка: <число>H<текст длиной число>
            hollerith = re.match(r"(\d+)H", raw[i:])
            if hollerith:
                length = int(hollerith.group(1))
                start_pos = i + len(hollerith.group(0))
                text = raw[start_pos : start_pos + length]
                current += hollerith.group(0) + text
                i = start_pos + length
            elif raw[i] in (",", ";"):
                params.append(current.strip())
                current = ""
                i += 1
            else:
                current += raw[i]
                i += 1
        if current.strip():
            params.append(current.strip())
        return params

    def _decode_hollerith(self, value: str) -> str | None:
        """Декодирует Hollerith-строку формата NHtext → text.

        Hollerith — способ кодирования строк в IGES: '6HRa 3.2' означает
        строку длиной 6 символов 'Ra 3.2'. Unicode (кириллица) поддерживается,
        так как входная строка уже декодирована как UTF-8 клиентом.
        """
        if not value:
            return None
        m = re.match(r"^(\d+)H(.*)$", value, re.DOTALL)
        if m:
            length = int(m.group(1))
            return m.group(2)[:length]
        # Числовое значение — не строка
        return value if value else None

    def _safe_int(self, value: str) -> int | None:
        try:
            return int(float(value.strip()))
        except (ValueError, AttributeError):
            return None

    def _safe_float(self, value: str) -> float | None:
        try:
            return float(value.strip())
        except (ValueError, AttributeError):
            return None

    def _build_metadata(self, params: list[str]) -> DrawingMetadata:
        """Маппит параметры P1-P26 на поля DrawingMetadata.

        Нумерация параметров по стандарту IGES 5.3 (1-indexed):
        P4  — имя файла / обозначение чертежа
        P13 — масштаб (Model Space Scale)
        P14 — код единицы измерения
        P18 — дата создания
        P21 — автор
        P22 — организация
        P23 — версия IGES
        P24 — код стандарта оформления
        P25 — дата последней модификации
        """

        def get(idx: int) -> str:
            # idx 1-based по стандарту IGES
            return params[idx - 1] if len(params) >= idx else ""

        unit_code = self._safe_int(get(14))
        unit = UNIT_MAP.get(unit_code, "unknown") if unit_code is not None else "unknown"

        drafting_code = self._safe_int(get(24))
        drafting_standard = DRAFTING_STANDARD_MAP.get(drafting_code, None)

        return DrawingMetadata(
            drawing_title=self._decode_hollerith(get(4)),
            author=self._decode_hollerith(get(21)),       # P21 по стандарту IGES 5.3
            organization=self._decode_hollerith(get(22)), # P22 по стандарту IGES 5.3
            unit=unit,
            unit_code=unit_code,
            scale=self._safe_float(get(13)),
            created_at=self._decode_hollerith(get(18)),
            modified_at=self._decode_hollerith(get(25)), # P25 — дата последней модификации
            iges_version=str(self._safe_int(get(23))) if get(23) else None,
            drafting_standard=drafting_standard,
        )
