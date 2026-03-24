"""Генератор тестовых IGES-фикстур.

Создаёт программно корректные 80-символьные IGES-файлы для тестирования.
Запустить вручную: python tests/fixtures/generate_fixtures.py

Бизнес-цель: гарантировать, что тестовые файлы строго соответствуют
стандарту IGES 5.3 по позициям полей, что исключает двусмысленность
при отладке тестов.
"""

from pathlib import Path

FIXTURES_DIR = Path(__file__).parent


def igs_line(data: str, section: str, seq: int) -> str:
    """Строит строго 80-символьную IGES-строку.

    Стандарт IGES требует:
    - Позиции 1-72 (0-indexed 0-71): данные секции
    - Позиция 73 (0-indexed 72): код секции (S/G/D/P/T)
    - Позиции 74-80 (0-indexed 73-79): порядковый номер (7 символов)
    """
    return f"{data[:72]:<72}{section}{seq:>7}"


def d_line1(entity_type: int, param_ptr: int, layer: int, seq: int) -> str:
    """Первая строка Directory Entry (9 полей × 8 символов)."""
    data = f"{entity_type:>8}{param_ptr:>8}       0       0{layer:>8}       0       0       0       0"
    return igs_line(data, "D", seq)


def d_line2(entity_type: int, line_weight: int, color: int, seq: int) -> str:
    """Вторая строка Directory Entry."""
    data = f"{entity_type:>8}{line_weight:>8}{color:>8}       0       0       0       0       0       0"
    return igs_line(data, "D", seq)


def p_line(de_seq: int, params_str: str, p_seq: int) -> str:
    """Строка Parameter Data (7-char DE seq + space + 64-char data)."""
    return igs_line(f"{de_seq:>7} {params_str}", "P", p_seq)


def build_g_section(
    filename: str,
    author: str,
    organization: str,
    unit_code: int = 2,
) -> tuple[str, str, str]:
    """Строит 3 строки G-секции (P1-P26 по IGES 5.3).

    P14 = unit_code: 2 = мм, 1 = дюймы.
    P21 = автор, P22 = организация — ключевые для паспорта детали.
    Hollerith-формат: NHtext, N = количество символов.
    """
    fname_h = f"{len(filename)}H{filename}"
    author_h = f"{len(author)}H{author}"
    org_h = f"{len(organization)}H{organization}"

    # G1: P1..P12 (до P12 включительно)
    # Подбираем длину P3/P4/P5/P6 чтобы уложиться в 72 символа
    g1 = f"1H,,1H;,5Hpart1,{fname_h},2Hv1,2Hv1,32,38,6,308,15,6Hpart01,"
    # G2: P13..P22
    g2 = f"1.,{unit_code},2HMM,16,0.10,15H20260324.120000,0.0010,500.,{author_h},{org_h},"
    # G3: P23..P26 + terminate
    g3 = "11,1,15H20260324.130000,;"

    return g1, g2, g3


def generate_kompas_sample() -> str:
    """Генерирует IGES-файл, имитирующий экспорт из Компас 3D.

    Содержит кириллические аннотации и размеры для тестирования
    корректности декодирования Hollerith-строк с Unicode.
    """
    # G-секция с кириллическими метаданными
    g1 = "1H,,1H;,5Hpart1,14Hкомпас_001.igs,2Hv1,2Hv1,32,38,6,308,15,6Hpart01,"
    g2 = "1.,2,2HMM,16,0.10,15H20260324.120000,0.0010,500.,7HИванов ,5HОКБ-7,"
    g3 = "11,1,15H20260324.130000,;"

    # Сущности: линия (110), кириллическое примечание (212), линейный размер (216)
    lines_out = [
        igs_line("", "S", 1),
        igs_line(g1, "G", 1),
        igs_line(g2, "G", 2),
        igs_line(g3, "G", 3),
        # DE: линия seq=1, кирилл. примечание seq=3, размер seq=5
        d_line1(110, 1, 0, 1), d_line2(110, 0, 0, 2),
        d_line1(212, 3, 0, 3), d_line2(212, 0, 0, 4),
        d_line1(216, 5, 0, 5), d_line2(216, 0, 0, 6),
        # P: линия 0..100, примечание с кириллицей, линейный размер
        p_line(1, "110,0.,0.,0.,100.,50.,0.;", 1),
        p_line(3, "212,1,3.5,1.0,4,5.,5.,0.,0.,0.,0.,18HСталь 45 ГОСТ 1050;", 2),
        p_line(5, "216,3,0.,-5.,100.,-5.;", 3),
        igs_line("", "T", 1),
    ]

    # Проверяем длины всех строк
    for i, ln in enumerate(lines_out):
        assert len(ln) == 80, f"Строка {i + 1}: длина {len(ln)} != 80"

    return "\n".join(lines_out) + "\n"


if __name__ == "__main__":
    content = generate_kompas_sample()
    out = FIXTURES_DIR / "kompas_sample.igs"
    out.write_text(content, encoding="utf-8")
    print(f"Написан: {out}")
