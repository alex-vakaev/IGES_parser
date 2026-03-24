"""T026 — Unit-тесты для IgesReader."""

import pytest

from src.parser.iges_reader import IgesFormatError, IgesReader


def _igs_line(data: str, section: str, seq: int) -> str:
    """Строит правильную 80-символьную IGES-строку (section code на позиции 72)."""
    return f"{data[:72]:<72}{section}{seq:>7}"


MINIMAL_IGES = "\n".join([
    _igs_line("", "S", 1),
    _igs_line("1H,,1H;,5Htest;", "G", 1),
    _igs_line(f"{'     110':>8}{'       1':>8}" + "       0" * 7, "D", 1),
    _igs_line(f"{'     110':>8}" + "       0" * 8, "D", 2),
    _igs_line("      1 110,0.,0.,0.,10.,0.,0.;", "P", 1),
    _igs_line("", "T", 1),
]) + "\n"


def test_split_sections_returns_all_five():
    """Валидный IGES разбивается на 5 непустых секций."""
    reader = IgesReader()
    sections = reader.split_sections(MINIMAL_IGES)
    assert len(sections.start_lines) > 0
    assert len(sections.global_lines) > 0
    assert len(sections.directory_lines) > 0
    assert len(sections.parameter_lines) > 0
    assert len(sections.terminate_lines) > 0


def test_split_sections_identifies_correct_codes():
    """Строки правильно распределяются по секциям."""
    reader = IgesReader()
    sections = reader.split_sections(MINIMAL_IGES)
    assert all(line[72] == "S" for line in sections.start_lines)
    assert all(line[72] == "G" for line in sections.global_lines)
    assert all(line[72] in ("D",) for line in sections.directory_lines)
    assert all(line[72] == "P" for line in sections.parameter_lines)


def test_invalid_content_raises_format_error():
    """Произвольный текст без IGES-секций поднимает IgesFormatError."""
    reader = IgesReader()
    with pytest.raises(IgesFormatError):
        reader.split_sections("This is not an IGES file at all.")


def test_empty_string_raises_format_error():
    """Пустая строка поднимает IgesFormatError."""
    reader = IgesReader()
    with pytest.raises(IgesFormatError):
        reader.split_sections("")
