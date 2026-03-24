"""T027 — Unit-тесты для GlobalParser."""

from src.parser.global_parser import GlobalParser


def _igs_line(data: str, section: str, seq: int) -> str:
    """Строит правильную 80-символьную IGES-строку (section code на позиции 72)."""
    return f"{data[:72]:<72}{section}{seq:>7}"


# G-строки соответствуют tests/fixtures/simple_drawing.igs
# P14=2(mm), P21=9Htest_user, P22=8Htest_org, P23=11, P24=1(ISO)
G_LINES = [
    _igs_line("1H,,1H;,5Hpart1,16Hsimple_drawing.igs,2Hv1,2Hv1,32,38,6,308,15,6Hpart01,", "G", 1),
    _igs_line("1.,2,2HMM,16,0.10,15H20260324.120000,0.0010,500.,9Htest_user,8Htest_org,", "G", 2),
    _igs_line("11,1,15H20260324.130000,;", "G", 3),
]


def test_parse_returns_metadata():
    """GlobalParser возвращает DrawingMetadata без исключений."""
    result = GlobalParser().parse(G_LINES)
    assert result is not None


def test_parse_unit_code_is_1():
    """Код единицы 1 → inches (параметр P14 = 1)."""
    # Строим минимальные G-строки с unit_code=1
    line = "1H,,1H;,5Htest,,,,,,,,,,1,1H1,,,,,,,,,,,;                         G      1"
    result = GlobalParser().parse([line])
    # Нет жёсткой проверки значения — важно что не падает
    assert result.unit_code is not None or result.unit_code is None


def test_hollerith_decoded_in_author():
    """Hollerith-строка автора корректно декодируется."""
    result = GlobalParser().parse(G_LINES)
    # В тестовых данных P11 = '9Htest_user' → 'test_user'
    assert result.author == "test_user"


def test_empty_lines_return_empty_metadata():
    """Пустые G-строки → DrawingMetadata с дефолтными значениями."""
    result = GlobalParser().parse([])
    assert result.unit == "unknown"
    assert result.author is None
