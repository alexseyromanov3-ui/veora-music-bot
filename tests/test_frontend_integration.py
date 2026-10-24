import pytest
from httpx import ASGITransport, AsyncClient
from src.api.app import app


@pytest.mark.asyncio
async def test_webapp_static_files():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Проверяем отдачу index.html по /webapp
        resp = await client.get("/webapp/")
        assert resp.status_code == 200
        assert "<title>VEORA Music Player</title>" in resp.text
        assert "player-dock" in resp.text
        assert "full-player" in resp.text

        # 2. Проверяем стили
        css_resp = await client.get("/webapp/styles.css")
        assert css_resp.status_code == 200
        assert "--accent-gradient" in css_resp.text

        # 3. Проверяем js модули
        db_resp = await client.get("/webapp/db.js")
        assert db_resp.status_code == 200
        assert "MusicBotOfflineDB" in db_resp.text

        player_resp = await client.get("/webapp/player.js")
        assert player_resp.status_code == 200
        assert "AudioPlayerEngine" in player_resp.text

        app_resp = await client.get("/webapp/app.js")
        assert app_resp.status_code == 200
        assert "document.addEventListener" in app_resp.text
