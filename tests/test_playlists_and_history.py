import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.app import app
from src.database.base import Base
from src.database.session import get_db
from src.models import Track, User
from tests.test_auth_and_storage import create_valid_init_data
from src.config import settings

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def full_client():
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
async def test_playlists_crud_and_tracks(full_client):
    client, session_maker = full_client
    init_data = create_valid_init_data(8888, "dj_producer", settings.BOT_TOKEN)
    headers = {"X-Telegram-Init-Data": init_data}

    # 1. Создаем плейлист
    resp = await client.post(
        "/api/playlists",
        json={"title": "Chill Vibes", "description": "Relaxing electronic music"},
        headers=headers,
    )
    assert resp.status_code == 201
    playlist_data = resp.json()
    playlist_id = playlist_data["id"]
    assert playlist_data["title"] == "Chill Vibes"

    # 2. Добавляем трек в БД
    async with session_maker() as session:
        track = Track(
            file_hash="hash_chill_1",
            title="Weightless",
            artist="Marconi Union",
            duration=480,
            file_size=12000000,
            file_path="dummy.mp3",
        )
        session.add(track)
        await session.commit()
        track_id = track.id

    # 3. Добавляем трек в плейлист
    add_resp = await client.post(
        f"/api/playlists/{playlist_id}/tracks",
        json={"track_id": track_id},
        headers=headers,
    )
    assert add_resp.status_code == 204

    # 4. Получаем детали плейлиста
    detail_resp = await client.get(f"/api/playlists/{playlist_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["tracks_count"] == 1
    assert detail["tracks"][0]["title"] == "Weightless"

    # 5. Удаляем трек из плейлиста
    del_track_resp = await client.delete(
        f"/api/playlists/{playlist_id}/tracks/{track_id}", headers=headers
    )
    assert del_track_resp.status_code == 204

    # Проверяем, что треков стало 0
    detail_after = (await client.get(f"/api/playlists/{playlist_id}", headers=headers)).json()
    assert detail_after["tracks_count"] == 0


@pytest.mark.asyncio
async def test_listening_history(full_client):
    client, session_maker = full_client
    init_data = create_valid_init_data(7777, "audio_phile", settings.BOT_TOKEN)
    headers = {"X-Telegram-Init-Data": init_data}

    async with session_maker() as session:
        t1 = Track(
            file_hash="h1",
            title="Track 1",
            artist="Artist A",
            duration=200,
            file_size=5000,
            file_path="1.mp3",
        )
        t2 = Track(
            file_hash="h2",
            title="Track 2",
            artist="Artist B",
            duration=180,
            file_size=4000,
            file_path="2.mp3",
        )
        session.add_all([t1, t2])
        await session.commit()
        t1_id, t2_id = t1.id, t2.id

    # Записываем историю
    rec1 = await client.post(
        "/api/history",
        json={"track_id": t1_id, "duration_played": 120},
        headers=headers,
    )
    assert rec1.status_code == 204

    rec2 = await client.post(
        "/api/history",
        json={"track_id": t2_id, "duration_played": 180},
        headers=headers,
    )
    assert rec2.status_code == 204

    # Получаем недавно прослушанные
    history_resp = await client.get("/api/history/recently-played", headers=headers)
    assert history_resp.status_code == 200
    items = history_resp.json()
    assert len(items) == 2
    assert items[0]["id"] == t2_id  # t2 играл последним


@pytest.mark.asyncio
async def test_track_metadata_patch(full_client):
    client, session_maker = full_client
    init_data = create_valid_init_data(9991, "editor_user", settings.BOT_TOKEN)
    headers = {"X-Telegram-Init-Data": init_data}

    # Авторизуем пользователя и создаем трек с его uploader_id
    auth_resp = await client.post("/api/auth/validate", json={"init_data": init_data})
    user_id = auth_resp.json()["user"]["id"]

    async with session_maker() as session:
        track = Track(
            file_hash="edit_hash_1",
            title="Old Wrong Title",
            artist="Unknown Artist",
            album="None",
            duration=150,
            file_size=3000,
            file_path="track.mp3",
            uploader_id=user_id,
        )
        session.add(track)
        await session.commit()
        track_id = track.id

    # Редактируем название и исполнителя
    patch_resp = await client.patch(
        f"/api/tracks/{track_id}",
        json={"title": "Get Lucky", "artist": "Daft Punk", "album": "Random Access Memories"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["title"] == "Get Lucky"
    assert updated["artist"] == "Daft Punk"
    assert updated["album"] == "Random Access Memories"
