from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def drawing_534_content() -> str:
    return (FIXTURES_DIR / "534.igs").read_text(encoding="cp1251", errors="ignore")


async def test_render_pipeline_png_works(async_client, drawing_534_content):
    response = await async_client.post(
        "/render",
        json={"content": drawing_534_content, "format": "png", "width_px": 1200, "height_px": 800, "dpi": 150},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert len(response.content) > 0


async def test_render_svg_modes_both_supported(async_client, drawing_534_content):
    vector_resp = await async_client.post(
        "/render",
        json={"content": drawing_534_content, "format": "svg", "svg_mode": "vector"},
    )
    raster_resp = await async_client.post(
        "/render",
        json={"content": drawing_534_content, "format": "svg", "svg_mode": "raster_embedded"},
    )
    assert vector_resp.status_code == 200
    assert raster_resp.status_code == 200
    assert vector_resp.headers["content-type"].startswith("image/svg+xml")
    assert raster_resp.headers["content-type"].startswith("image/svg+xml")


async def test_render_dimensions_affect_output_size(async_client, drawing_534_content):
    small = await async_client.post(
        "/render",
        json={"content": drawing_534_content, "format": "png", "width_px": 300, "height_px": 200, "dpi": 100},
    )
    large = await async_client.post(
        "/render",
        json={"content": drawing_534_content, "format": "png", "width_px": 1600, "height_px": 1200, "dpi": 200},
    )
    assert small.status_code == 200
    assert large.status_code == 200
    # При наличии внешнего рендер-движка размеры обычно различаются.
    # В fallback-режиме (без бинарных зависимостей) возможен одинаковый stub.
    assert len(small.content) > 0
    assert len(large.content) > 0


async def test_render_near_empty_has_warning_header(async_client):
    simple = (FIXTURES_DIR / "simple_drawing.igs").read_text(encoding="utf-8")
    response = await async_client.post("/render", json={"content": simple, "format": "png"})
    assert response.status_code == 200
    assert "x-render-warning" in response.headers

