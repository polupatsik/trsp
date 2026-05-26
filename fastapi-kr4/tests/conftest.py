import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app, db


@pytest_asyncio.fixture
async def client():
    db.clear()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    db.clear()
