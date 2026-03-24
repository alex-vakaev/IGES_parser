from src.models.internal import EntityHeader


class DirectoryParser:
    """Читает Directory Entry (D) секцию и строит карту сущностей.

    Directory Entry содержит «оглавление» IGES-файла: по 2 строки на сущность,
    каждая строка ровно 80 символов с фиксированными полями по 8 символов.
    Позиция 73-79 каждой строки — её порядковый номер в секции.

    Структура первой строки DE (поля по 8 символов):
      Field 1  (cols 1-8):  entity_type
      Field 2  (cols 9-16): param_data_ptr  — указатель на строку P-секции
      Field 3  (cols 17-24): structure
      Field 4  (cols 25-32): line_font
      Field 5  (cols 33-40): layer
      Field 6  (cols 41-48): view
      Field 7  (cols 49-56): transform_matrix
      Field 8  (cols 57-64): label_display
      Field 9  (cols 65-72): status / blank_status
      Field 10 (col 73):    section code 'D'
      Fields 73-80:         sequence_number (нечётный)

    Второй строки:
      Field 11 (cols 1-8):  entity_type (повтор)
      Field 12 (cols 9-16): line_weight
      Field 13 (cols 17-24): color
      ...

    Бизнес-цель: связать порядковые номера с типами сущностей, чтобы
    EntityDispatcher знал, какой парсер вызвать для каждой P-записи.
    """

    FIELD_WIDTH = 8

    def parse(self, d_lines: list[str]) -> dict[int, EntityHeader]:
        """Парсит строки D-секции → словарь sequence_number → EntityHeader.

        Строки идут парами (DE состоит из 2 строк на сущность).
        Нечётные строки — первая запись, чётные — вторая.
        """
        directory: dict[int, EntityHeader] = {}

        # Обрабатываем попарно
        for i in range(0, len(d_lines) - 1, 2):
            line1 = d_lines[i]
            line2 = d_lines[i + 1] if i + 1 < len(d_lines) else ""

            header = self._parse_pair(line1, line2)
            if header:
                directory[header.sequence_number] = header

        return directory

    def _field(self, line: str, field_index: int) -> str:
        """Извлекает одно 8-символьное поле DE по его индексу (0-based)."""
        start = field_index * self.FIELD_WIDTH
        return line[start : start + self.FIELD_WIDTH].strip()

    def _safe_int(self, value: str) -> int | None:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _parse_pair(self, line1: str, line2: str) -> EntityHeader | None:
        """Разбирает пару строк DE и возвращает EntityHeader."""
        if len(line1) < 72:
            return None

        entity_type = self._safe_int(self._field(line1, 0))
        if entity_type is None:
            return None

        param_data_ptr = self._safe_int(self._field(line1, 1)) or 0

        # Слой (Level) — поле 5 первой строки
        layer = self._safe_int(self._field(line1, 4))

        # Порядковый номер — 7 символов после кода секции 'D' (0-indexed 73-79)
        seq_str = line1[73:80].strip() if len(line1) >= 80 else line1[73:].strip()
        sequence_number = self._safe_int(seq_str)
        if sequence_number is None:
            return None

        # line_weight и color — из второй строки DE
        line_weight = self._safe_int(self._field(line2, 1)) if len(line2) >= 8 else None
        color = self._safe_int(self._field(line2, 2)) if len(line2) >= 16 else None

        return EntityHeader(
            entity_type=entity_type,
            sequence_number=sequence_number,
            param_data_ptr=param_data_ptr,
            layer=layer,
            color=color,
            line_weight=line_weight,
        )
