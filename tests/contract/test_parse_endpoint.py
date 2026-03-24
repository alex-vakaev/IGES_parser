"""T013 + T029 — Contract-тесты POST /parse: успех и все коды ошибок.

Проверяет HTTP-статусы и структуру JSON по контракту contracts/parse.md.
Тесты не зависят от деталей парсинга — только от формы ответа и error_code.
"""

from pathlib import Path

import pytest


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def simple_iges_content() -> str:
    return (FIXTURES_DIR / "simple_drawing.igs").read_text(encoding="utf-8")


async def test_parse_returns_200_with_correct_structure(async_client, simple_iges_content):
    """POST /parse с валидным IGES возвращает HTTP 200 и все обязательные поля."""
    response = await async_client.post("/parse", json={"content": simple_iges_content})
    assert response.status_code == 200
    body = response.json()
    assert "drawing_metadata" in body
    assert "geometry" in body
    assert "dimensions" in body
    assert "annotations" in body
    assert "summary" in body
    assert "unsupported_entities" in body


async def test_parse_metadata_has_required_fields(async_client, simple_iges_content):
    """drawing_metadata содержит поле unit."""
    response = await async_client.post("/parse", json={"content": simple_iges_content})
    assert response.status_code == 200
    metadata = response.json()["drawing_metadata"]
    assert "unit" in metadata


async def test_parse_summary_has_required_fields(async_client, simple_iges_content):
    """summary содержит entity_counts, total_entities, units."""
    response = await async_client.post("/parse", json={"content": simple_iges_content})
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert "entity_counts" in summary
    assert "total_entities" in summary
    assert "units" in summary


async def test_parse_empty_content_returns_400(async_client):
    """Пустой content → HTTP 400 EMPTY_INPUT."""
    response = await async_client.post("/parse", json={"content": ""})
    assert response.status_code == 400


async def test_parse_non_iges_content_returns_422(async_client):
    """Не-IGES текст → HTTP 422 INVALID_FORMAT."""
    response = await async_client.post("/parse", json={"content": "Hello, this is not IGES"})
    assert response.status_code == 422
    body = response.json()
    # FastAPI оборачивает detail в свою структуру
    detail = body.get("detail", body)
    if isinstance(detail, dict):
        assert detail.get("error_code") == "INVALID_FORMAT"


async def test_health_returns_ok(async_client):
    """GET /health возвращает {"status": "ok"}."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# T029: Тесты ошибочных ответов (US2)
# ---------------------------------------------------------------------------

async def test_empty_content_error_has_correct_schema(async_client):
    """HTTP 400 при пустом content содержит error_code EMPTY_INPUT."""
    response = await async_client.post("/parse", json={"content": ""})
    assert response.status_code == 400
    detail = response.json().get("detail", response.json())
    assert detail.get("error_code") == "EMPTY_INPUT"
    assert "message" in detail
    assert "details" in detail


async def test_whitespace_only_content_returns_400(async_client):
    """Контент только из пробелов → HTTP 400 EMPTY_INPUT."""
    response = await async_client.post("/parse", json={"content": "   \n\t  "})
    assert response.status_code == 400
    detail = response.json().get("detail", response.json())
    assert detail.get("error_code") == "EMPTY_INPUT"


async def test_invalid_format_error_has_correct_schema(async_client):
    """HTTP 422 при не-IGES тексте содержит error_code INVALID_FORMAT."""
    response = await async_client.post("/parse", json={"content": "random text without IGES structure"})
    assert response.status_code == 422
    detail = response.json().get("detail", response.json())
    assert detail.get("error_code") == "INVALID_FORMAT"
    assert "message" in detail


async def test_size_exceeded_returns_413(async_client):
    """Запрос с Content-Length > лимита → HTTP 413 SIZE_EXCEEDED."""
    # Отправляем заголовок Content-Length > MAX_CONTENT_BYTES (10MB default)
    big_size = 10 * 1024 * 1024 + 1
    response = await async_client.post(
        "/parse",
        json={"content": "x"},
        headers={"content-length": str(big_size)},
    )
    assert response.status_code == 413
    body = response.json()
    assert body.get("error_code") == "SIZE_EXCEEDED"


async def test_missing_content_field_returns_422(async_client):
    """Отсутствующее поле content → HTTP 422 (Pydantic validation)."""
    response = await async_client.post("/parse", json={"wrong_field": "data"})
    assert response.status_code == 422


async def test_non_json_body_returns_422(async_client):
    """Не-JSON тело → HTTP 422 или 400."""
    response = await async_client.post(
        "/parse",
        content=b"not json at all",
        headers={"content-type": "application/json"},
    )
    assert response.status_code in (400, 422)


async def test_error_response_never_leaks_traceback(async_client):
    """Ответ при ошибке не содержит Python traceback."""
    response = await async_client.post("/parse", json={"content": "not iges"})
    text = response.text
    assert "Traceback" not in text
    assert "File \"" not in text
