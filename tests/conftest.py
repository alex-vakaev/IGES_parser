import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture
async def async_client() -> AsyncClient:
    """Фикстура httpx AsyncClient с ASGI transport.

    Позволяет тестировать FastAPI-приложение напрямую через ASGI,
    без поднятия реального HTTP-сервера. Быстро, без сетевых задержек.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
