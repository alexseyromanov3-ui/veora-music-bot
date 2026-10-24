import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.app import app
from src.database.base import Base
from src.database.session import get_db
from src.models import Track, User, UserTrack
from tests.test_auth_and_storage import create_valid_init_data
from src.config import settings

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def social_client():
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
async def test_friends_connect_and_tracks(social_client):
    client, session_maker = social_client
    u1_init = create_valid_init_data(101, "alice", settings.BOT_TOKEN)
    u2_init = create_valid_init_data(102, "bob", settings.BOT_TOKEN)

    # Регистрируем обоих пользователей
    await client.post("/api/auth/validate", json={"init_data": u1_init})
    await client.post("/api/auth/validate", json={"init_data": u2_init})

    # Bob загружает публичный трек и приватный трек
    async with session_maker() as session:
        t_pub = Track(
            file_hash="hash_bob_public",
            title="Bob's Hit",
            artist="Bob Artist",
            duration=190,
            file_size=6000,
            file_path="bob.mp3",
            uploader_id=102,
            is_private=False,
        )
        t_priv = Track(
            file_hash="hash_bob_private",
            title="Secret Demo",
            artist="Bob Artist",
            duration=120,
            file_size=4000,
            file_path="secret.mp3",
            uploader_id=102,
            is_private=True,
        )
        session.add_all([t_pub, t_priv])
        await session.commit()

    # 1. Alice подключает Bob в друзья по инвайту
    conn_resp = await client.post(
        "/api/social/friends/connect",
        json={"friend_id": 102},
        headers={"X-Telegram-Init-Data": u1_init},
    )
    assert conn_resp.status_code == 200
    assert conn_resp.json()["success"] is True

    # 2. Alice проверяет список друзей
    friends_resp = await client.get(
        "/api/social/friends", headers={"X-Telegram-Init-Data": u1_init}
    )
    assert friends_resp.status_code == 200
    friends = friends_resp.json()
    assert len(friends) == 1
    assert friends[0]["id"] == 102
    assert friends[0]["tracks_count"] == 1  # только 1 публичный трек

    # 3. Alice смотрит ленту треков друзей
    friend_tracks_resp = await client.get(
        "/api/social/friends/tracks", headers={"X-Telegram-Init-Data": u1_init}
    )
    assert friend_tracks_resp.status_code == 200
    f_tracks = friend_tracks_resp.json()
    assert f_tracks["total"] == 1
    assert f_tracks["items"][0]["title"] == "Bob's Hit"
    assert f_tracks["items"][0]["uploader_name"] == "@bob"


@pytest.mark.asyncio
async def test_recommendations_engine(social_client):
    client, session_maker = social_client
    u_init = create_valid_init_data(201, "charlie", settings.BOT_TOKEN)
    await client.post("/api/auth/validate", json={"init_data": u_init})

    async with session_maker() as session:
        # У Charlie в избранном есть трек Daft Punk
        t1 = Track(
            file_hash="h_dp1",
            title="One More Time",
            artist="Daft Punk",
            duration=320,
            file_size=7000,
            file_path="dp1.mp3",
            is_private=False,
        )
        # В сообществе есть другой трек Daft Punk, которого у Charlie нет
        t2 = Track(
            file_hash="h_dp2",
            title="Harder Better Faster",
            artist="Daft Punk",
            duration=224,
            file_size=6000,
            file_path="dp2.mp3",
            is_private=False,
        )
        session.add_all([t1, t2])
        await session.commit()

        # Добавляем t1 в избранное Charlie
        ut = UserTrack(user_id=201, track_id=t1.id, is_favorite=True)
        session.add(ut)
        await session.commit()

    # Запрашиваем рекомендации «Для вас»
    rec_resp = await client.get(
        "/api/social/recommendations", headers={"X-Telegram-Init-Data": u_init}
    )
    assert rec_resp.status_code == 200
    rec_items = rec_resp.json()
    assert len(rec_items) >= 1
    # Алгоритм должен порекомендовать второй трек Daft Punk
    assert any(t["title"] == "Harder Better Faster" for t in rec_items)


@pytest.mark.asyncio
async def test_community_feed_and_privacy_toggle(social_client):
    client, session_maker = social_client
    u_init = create_valid_init_data(301, "david", settings.BOT_TOKEN)
    await client.post("/api/auth/validate", json={"init_data": u_init})

    async with session_maker() as session:
        t = Track(
            file_hash="h_david1",
            title="David's Track",
            artist="David",
            duration=200,
            file_size=5000,
            file_path="david.mp3",
            uploader_id=301,
            is_private=False,
        )
        session.add(t)
        await session.commit()
        await session.refresh(t)
        track_id = t.id

    # 1. Проверяем Ленту сообщества - трек виден
    comm_resp = await client.get(
        "/api/social/community", headers={"X-Telegram-Init-Data": u_init}
    )
    assert comm_resp.status_code == 200
    comm_data = comm_resp.json()
    assert any(it["id"] == track_id for it in comm_data["items"])

    # 2. Делаем трек приватным через toggle-privacy
    toggle_resp = await client.post(
        f"/api/tracks/{track_id}/toggle-privacy",
        headers={"X-Telegram-Init-Data": u_init},
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["is_private"] is True

    # 3. Теперь в публичной Ленте сообщества трека быть не должно
    comm_resp2 = await client.get(
        "/api/social/community", headers={"X-Telegram-Init-Data": u_init}
    )
    assert comm_resp2.status_code == 200
    comm_data2 = comm_resp2.json()
    assert not any(it["id"] == track_id for it in comm_data2["items"])

    # 4. Переключаем обратно в публичный
    toggle_resp2 = await client.post(
        f"/api/tracks/{track_id}/toggle-privacy",
        headers={"X-Telegram-Init-Data": u_init},
    )
    assert toggle_resp2.status_code == 200
    assert toggle_resp2.json()["is_private"] is False
