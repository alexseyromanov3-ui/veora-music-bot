import hashlib
import hmac
import json
import time
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.app import app
from src.database.base import Base
from src.database.session import get_db
from src.models import Track, User, UserTrack
from src.services.storage import storage_service

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def api_client():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session_maker

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_health_check(api_client):
    client, _ = api_client
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_api_tracks_and_range_streaming(api_client, tmp_path):
    client, session_maker = api_client

    # Создаем фиктивный аудиофайл
    dummy_audio_bytes = b"ID3_MOCK_DATA_" + b"0123456789" * 100  # 1014 байт
    audio_file = tmp_path / "test_track.mp3"
    audio_file.write_bytes(dummy_audio_bytes)

    # Добавляем трек в БД
    async with session_maker() as session:
        user = User(id=555, first_name="Tester")
        session.add(user)
        await session.commit()

        track = Track(
            file_hash="test_stream_hash_123",
            title="Stream Test Song",
            artist="Synth Artist",
            duration=120,
            file_size=len(dummy_audio_bytes),
            file_path=str(audio_file),
            uploader_id=user.id,
        )
        session.add(track)
        await session.commit()
        track_id = track.id

    # 1. Проверяем получение списка треков
    resp = await client.get("/api/tracks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Stream Test Song"

    # 2. Проверяем полный запрос стриминга (HTTP 200)
    stream_full = await client.get(f"/api/tracks/{track_id}/stream")
    assert stream_full.status_code == 200
    assert stream_full.headers["Accept-Ranges"] == "bytes"
    assert stream_full.content == dummy_audio_bytes

    # 3. Проверяем частичный HTTP Range запрос (HTTP 206 Partial Content)
    # Запрашиваем байты 10-29 (20 байт)
    range_resp = await client.get(
        f"/api/tracks/{track_id}/stream",
        headers={"Range": "bytes=10-29"},
    )
    assert range_resp.status_code == 206
    assert range_resp.headers["Content-Range"] == f"bytes 10-29/{len(dummy_audio_bytes)}"
    assert range_resp.headers["Content-Length"] == "20"
    # 4. Проверяем полное удаление трека
    from tests.test_auth_and_storage import create_valid_init_data
    from src.config import settings
    init_data = create_valid_init_data(555, "tester", settings.BOT_TOKEN)
    del_resp = await client.delete(
        f"/api/tracks/{track_id}",
        headers={"X-Telegram-Init-Data": init_data},
    )
    assert del_resp.status_code == 204

    # Проверяем, что в списке треков пусто
    list_after_del = await client.get("/api/tracks")
    assert list_after_del.json()["total"] == 0
