from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def simple_iges_content() -> str:
    return (FIXTURES_DIR / "simple_drawing.igs").read_text(encoding="utf-8")


async def test_render_png_returns_image(async_client, simple_iges_content):
    response = await async_client.post(
        "/render",
        json={"content": simple_iges_content, "format": "png"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.headers.get("x-render-format") == "png"
    assert int(response.headers.get("x-render-size-bytes", "0")) > 0
    assert len(response.content) > 0


async def test_render_jpg_returns_image(async_client, simple_iges_content):
    response = await async_client.post(
        "/render",
        json={"content": simple_iges_content, "format": "jpg"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/jpeg")


async def test_render_svg_returns_document(async_client, simple_iges_content):
    response = await async_client.post(
        "/render",
        json={"content": simple_iges_content, "format": "svg", "svg_mode": "vector"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in response.content


async def test_render_empty_input_returns_error(async_client):
    response = await async_client.post("/render", json={"content": "   ", "format": "png"})
    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "EMPTY_INPUT"


async def test_render_invalid_options_returns_error(async_client, simple_iges_content):
    response = await async_client.post(
        "/render",
        json={"content": simple_iges_content, "format": "png", "width_px": 10},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_RENDER_OPTIONS"


async def test_render_invalid_format_returns_error(async_client):
    response = await async_client.post("/render", json={"content": "not iges", "format": "png"})
    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == "INVALID_FORMAT"


async def test_render_engine_error_returns_render_error(async_client, simple_iges_content, monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("src.api.router.render_iges_image", _boom)
    response = await async_client.post("/render", json={"content": simple_iges_content, "format": "png"})
    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == "RENDER_ERROR"

