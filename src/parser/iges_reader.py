from src.models.internal import IgesSections


class IgesFormatError(ValueError):
    """Входной текст не является валидным IGES-файлом."""


class IgesReader:
    """Разбивает текстовый IGES-файл на 5 именованных секций.

    Стандарт IGES определяет ASCII-файл с фиксированными строками по 80 символов.
    Позиция 73 каждой строки (0-indexed 72) содержит код секции:
      S — Start (комментарии, читаемые людьми)
      G — Global (метаданные: автор, единицы, версия)
      D — Directory Entry (оглавление сущностей)
      P — Parameter Data (геометрия и аннотации)
      T — Terminate (последняя строка файла)

    Бизнес-цель: получить чистые строки каждой секции для дальнейшей
    обработки специализированными парсерами.
    """

    # Коды секций по стандарту IGES 5.3
    SECTION_CODES = {"S", "G", "D", "P", "T"}
    # Позиция кода секции в каждой строке (0-indexed)
    SECTION_CODE_POS = 72

    def split_sections(self, text: str) -> IgesSections:
        """Разбивает IGES-текст на секции по символу в столбце 73 (1-based) = индекс 72 (0-based).

        Строки короче 73 символов обрабатываются без паники: код секции
        считается отсутствующим и строка пропускается.

        Некоторые клиенты передают содержимое файла с буквальными \\n (два символа)
        вместо реальных переносов строк. В этом случае выполняем нормализацию.
        """
        # Нормализация: буквальные \n (backslash + n) → реальный перенос строки.
        # Применяем только если в тексте нет ни одного реального переноса — это
        # гарантирует, что не трогаем файлы с настоящими переносами.
        if "\n" not in text and r"\n" in text:
            text = text.replace(r"\n", "\n")

        sections = IgesSections()
        lines = text.splitlines()

        found_codes: set[str] = set()

        for line in lines:
            # Стандарт IGES: код секции на позиции 72 (0-indexed).
            # Некоторые CAD-экспортёры и вручную построенные файлы могут давать
            # строки длиной 79 вместо 80 — допускаем сдвиг на 1 позицию влево.
            code = None
            for check_pos in (self.SECTION_CODE_POS, self.SECTION_CODE_POS - 1):
                if len(line) > check_pos and line[check_pos].upper() in self.SECTION_CODES:
                    code = line[check_pos].upper()
                    break
            if code is None:
                continue
            found_codes.add(code)
            match code:
                case "S":
                    sections.start_lines.append(line)
                case "G":
                    sections.global_lines.append(line)
                case "D":
                    sections.directory_lines.append(line)
                case "P":
                    sections.parameter_lines.append(line)
                case "T":
                    sections.terminate_lines.append(line)

        # T031: проверяем наличие признаков IGES-файла.
        # Достаточно одной из ключевых секций чтобы идентифицировать файл как IGES.
        # Отсутствие всех — признак того, что передан произвольный текст.
        if not found_codes:
            raise IgesFormatError(
                "Не найдена ни одна IGES-секция (S/G/D/P/T). "
                "Переданный контент не является валидным IGES-файлом."
            )

        # Файл без G-секции не может быть корректно распарсен (нет метаданных),
        # но мы возвращаем то, что нашли — роутер получит пустые метаданные
        return sections
