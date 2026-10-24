from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient
from src.api.app import app
from src.config import settings
from src.models import Track
from tests.test_auth_and_storage import create_valid_init_data


@pytest.mark.asyncio
async def test_soundcloud_search_endpoint():
    mock_results = [
        {
            "id": "123",
            "title": "Phonk Test",
            "artist": "Test Artist",
            "duration": 180,
            "thumbnail": "https://example.com/art.jpg",
            "url": "https://soundcloud.com/test/track",
            "source": "soundcloud",
        }
    ]

    init_data = create_valid_init_data(1, "tester", settings.BOT_TOKEN)
    headers = {"X-Telegram-Init-Data": init_data}
    with patch("src.services.soundcloud_service.soundcloud_service.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_results

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/search/soundcloud?q=phonk&limit=5", headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["query"] == "phonk"
            assert data["total"] == 1
            assert data["items"][0]["title"] == "Phonk Test"
            assert data["items"][0]["artist"] == "Test Artist"


@pytest.mark.asyncio
async def test_soundcloud_import_endpoint():
    mock_track = Track(
        id=99,
        file_hash="mockhash99",
        title="Imported Phonk",
        artist="DJ Phonk",
        album="SoundCloud",
        duration=145,
        bit_rate=192000,
        file_size=3000000,
        mime_type="audio/mpeg",
        file_path="mock.mp3",
        cover_path="/pic/cover.jpg",
        telegram_file_id="tgfile99",
        uploader_id=1,
        is_private=False,
        created_at=datetime.now(timezone.utc),
    )

    init_data = create_valid_init_data(1, "tester", settings.BOT_TOKEN)
    headers = {"X-Telegram-Init-Data": init_data}
    with patch("src.services.soundcloud_service.soundcloud_service.import_track", new_callable=AsyncMock) as mock_import:
        mock_import.return_value = (mock_track, True)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {"url": "https://soundcloud.com/test/track"}
            resp = await client.post("/api/search/soundcloud/import", json=payload, headers=headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["track"]["id"] == 99
            assert data["track"]["title"] == "Imported Phonk"
            assert data["track"]["artist"] == "DJ Phonk"
