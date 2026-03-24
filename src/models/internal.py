from dataclasses import dataclass, field


@dataclass
class IgesSections:
    """Результат разбивки IGES-файла на 5 именованных секций.

    IGES-файл состоит из строк, каждая из которых имеет идентификатор
    секции в позиции 73: S=Start, G=Global, D=Directory Entry,
    P=Parameter Data, T=Terminate.
    """

    start_lines: list[str] = field(default_factory=list)
    global_lines: list[str] = field(default_factory=list)
    directory_lines: list[str] = field(default_factory=list)
    parameter_lines: list[str] = field(default_factory=list)
    terminate_lines: list[str] = field(default_factory=list)


@dataclass
class EntityHeader:
    """Заголовок сущности из Directory Entry (DE) секции.

    DE содержит 2 строки по 80 символов с фиксированными полями 8 символов.
    Каждая сущность идентифицируется entity_type и sequence_number,
    который служит ключом для связи с Parameter Data секцией.
    """

    entity_type: int
    sequence_number: int  # нечётный номер строки DE (1, 3, 5, ...)
    param_data_ptr: int = 0  # указатель на строку в P-секции
    layer: int | None = None
    color: int | None = None
    line_weight: int | None = None
    line_font: int | None = None
    status: str = ""


@dataclass
class RawEntity:
    """Сырые данные одной сущности перед типизированным парсингом.

    Объединяет header из DE и список параметров из P-секции.
    Используется EntityDispatcher для маршрутизации к нужному парсеру.
    """

    header: EntityHeader
    parameters: list[str]  # параметры через запятую из P-секции
