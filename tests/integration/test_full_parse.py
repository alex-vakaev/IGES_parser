"""T014 + T036 — Integration-тесты полного цикла парсинга.

Проверяет end-to-end: IGES-файл → POST /parse → структурированный JSON.
T014: базовый чертёж (simple_drawing.igs).
T036: кириллика из Компас 3D (kompas_sample.igs).
"""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def simple_iges_content() -> str:
    return (FIXTURES_DIR / "simple_drawing.igs").read_text(encoding="utf-8")


async def test_geometry_list_is_not_empty(async_client, simple_iges_content):
    """Чертёж с линией возвращает непустой список geometry."""
    response = await async_client.post("/parse", json={"content": simple_iges_content})
    assert response.status_code == 200
    assert len(response.json()["geometry"]) > 0


async def test_geometry_entity_has_coordinates(async_client, simple_iges_content):
    """Каждый геометрический объект содержит coordinates и raw_parameters."""
    response = await async_client.post("/parse", json={"content": simple_iges_content})
    for entity in response.json()["geometry"]:
        assert "coordinates" in entity
        assert "raw_parameters" in entity
        assert isinstance(entity["raw_parameters"], list)


async def test_annotations_contain_ra_note(async_client, simple_iges_content):
    """Текстовые примечания содержат 'Ra 3.2' из тестового файла."""
    response = await async_client.post("/parse", json={"content": simple_iges_content})
    assert response.status_code == 200
    contents = [a["content"] for a in response.json()["annotations"]]
    assert any("Ra" in c or "3.2" in c for c in contents), (
        f"Ожидалось примечание 'Ra 3.2', получено: {contents}"
    )


async def test_summary_bounding_box_not_none(async_client, simple_iges_content):
    """Для чертежа с геометрией bounding_box не None."""
    response = await async_client.post("/parse", json={"content": simple_iges_content})
    assert response.status_code == 200
    bbox = response.json()["summary"]["bounding_box"]
    assert bbox is not None
    assert "min_x" in bbox and "max_x" in bbox


async def test_summary_units_matches_metadata(async_client, simple_iges_content):
    """summary.units совпадает с drawing_metadata.unit."""
    response = await async_client.post("/parse", json={"content": simple_iges_content})
    body = response.json()
    assert body["summary"]["units"] == body["drawing_metadata"]["unit"]


# ---------------------------------------------------------------------------
# T036: Тесты кириллики (Компас 3D / US3)
# ---------------------------------------------------------------------------

@pytest.fixture
def kompas_iges_content() -> str:
    return (FIXTURES_DIR / "kompas_sample.igs").read_text(encoding="utf-8")


async def test_kompas_parse_returns_200(async_client, kompas_iges_content):
    """Компас-файл с кириллицей успешно парсится → HTTP 200."""
    response = await async_client.post("/parse", json={"content": kompas_iges_content})
    assert response.status_code == 200


async def test_kompas_annotations_contain_cyrillic(async_client, kompas_iges_content):
    """Аннотации из Компас-файла содержат корректный Unicode без замены символов."""
    response = await async_client.post("/parse", json={"content": kompas_iges_content})
    assert response.status_code == 200
    annotations = response.json()["annotations"]
    # Хотя бы одна аннотация должна содержать кириллицу
    all_content = " ".join(a["content"] for a in annotations)
    # Проверяем что нет символов замены (U+FFFD) и нет вопросительных знаков
    assert "\ufffd" not in all_content, "Символы кириллицы повреждены (U+FFFD)"
    assert "?" not in all_content, f"Символы кириллицы заменены на '?': {all_content!r}"
    # Хотя бы одна аннотация содержит кириллические символы
    has_cyrillic = any(
        any("\u0400" <= ch <= "\u04ff" for ch in a["content"])
        for a in annotations
    )
    assert has_cyrillic, f"Кириллика не найдена в аннотациях: {all_content!r}"


async def test_kompas_summary_bounding_box_not_none(async_client, kompas_iges_content):
    """Компас-файл с геометрией → bounding_box не None."""
    response = await async_client.post("/parse", json={"content": kompas_iges_content})
    assert response.status_code == 200
    bbox = response.json()["summary"]["bounding_box"]
    assert bbox is not None


async def test_kompas_summary_units_is_mm(async_client, kompas_iges_content):
    """Единицы из Компас-файла (P14=2) → summary.units = 'mm'."""
    response = await async_client.post("/parse", json={"content": kompas_iges_content})
    assert response.status_code == 200
    assert response.json()["summary"]["units"] == "mm"


async def test_kompas_author_is_cyrillic(async_client, kompas_iges_content):
    """Имя автора из Компас-файла декодируется как кириллица."""
    response = await async_client.post("/parse", json={"content": kompas_iges_content})
    assert response.status_code == 200
    author = response.json()["drawing_metadata"].get("author", "")
    if author:  # может быть None для файлов без автора
        has_cyrillic = any("\u0400" <= ch <= "\u04ff" for ch in author)
        assert has_cyrillic, f"Автор не кириллический: {author!r}"
