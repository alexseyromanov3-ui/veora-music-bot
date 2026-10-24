import asyncio
import hashlib
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import aiohttp
import yt_dlp
from aiogram import Bot
from aiogram.types import BufferedInputFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.models import Track, UserTrack
from src.services.track_service import track_service

logger = logging.getLogger("soundcloud_service")


class SoundCloudService:
    """Сервис поиска и загрузки музыки из SoundCloud с сохранением в Telegram Storage."""

    _bot_instance: Optional[Bot] = None

    @classmethod
    def get_bot(cls) -> Optional[Bot]:
        """Получить синглтон Telegram Bot для отправки аудио в канал-хранилище."""
        if settings.BOT_TOKEN in ("MOCK_TOKEN", "", "change_me"):
            return None
        if cls._bot_instance is None:
            cls._bot_instance = Bot(token=settings.BOT_TOKEN)
        return cls._bot_instance

    @staticmethod
    def _sync_search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Синхронный поиск треков в SoundCloud через yt-dlp."""
        ydl_opts = {
            "quiet": True,
            "extract_flat": True,
            "noplaylist": True,
            "ignoreerrors": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_str = f"scsearch{limit}:{query}"
            info = ydl.extract_info(search_str, download=False)
            entries = info.get("entries", []) if info else []
            results = []
            for e in entries:
                if not e:
                    continue

                raw_title = str(e.get("title") or "Трек").strip()
                uploader = str(e.get("uploader") or "SoundCloud").strip()

                if " - " in raw_title:
                    parts = raw_title.split(" - ", 1)
                    artist = parts[0].strip()
                    title = parts[1].strip()
                else:
                    artist = uploader
                    title = raw_title

                duration = int(float(e.get("duration") or 0))

                thumbnails = e.get("thumbnails", [])
                thumb = None
                if thumbnails:
                    thumb = thumbnails[-1].get("url")
                elif e.get("thumbnail"):
                    thumb = e.get("thumbnail")

                track_url = e.get("url") or e.get("webpage_url")
                if not track_url:
                    continue

                results.append({
                    "id": str(e.get("id") or track_url),
                    "title": title,
                    "artist": artist,
                    "duration": duration,
                    "thumbnail": thumb,
                    "url": track_url,
                    "source": "soundcloud",
                })
            return results

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Асинхронный поиск треков в SoundCloud."""
        if not query or not query.strip():
            return []
        return await asyncio.to_thread(self._sync_search, query.strip(), limit)

    @staticmethod
    def _sync_download(url: str) -> Tuple[bytes, Dict[str, Any]]:
        """Синхронная загрузка и конвертация аудио в MP3 (192kbps)."""
        tmp_id = uuid.uuid4().hex
        outtmpl = os.path.join(tempfile.gettempdir(), f"sc_{tmp_id}.%(ext)s")
        mp3_path = os.path.join(tempfile.gettempdir(), f"sc_{tmp_id}.mp3")

        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "outtmpl": outtmpl,
            "quiet": True,
            "noplaylist": True,
            "ignoreerrors": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            raw_title = str(info.get("title") or "SoundCloud Track").strip()
            uploader = str(info.get("uploader") or "SoundCloud").strip()

            if " - " in raw_title:
                parts = raw_title.split(" - ", 1)
                artist = parts[0].strip()
                title = parts[1].strip()
            else:
                artist = uploader
                title = raw_title

            duration = int(float(info.get("duration") or 0))
            thumbnail = info.get("thumbnail")

        if not os.path.exists(mp3_path):
            for ext in (".mp3", ".m4a", ".opus", ".webm"):
                cand = os.path.join(tempfile.gettempdir(), f"sc_{tmp_id}{ext}")
                if os.path.exists(cand):
                    mp3_path = cand
                    break

        if not os.path.exists(mp3_path):
            raise RuntimeError("Не удалось извлечь MP3 поток с SoundCloud")

        try:
            with open(mp3_path, "rb") as f:
                file_bytes = f.read()
        finally:
            if os.path.exists(mp3_path):
                try:
                    os.remove(mp3_path)
                except Exception:
                    pass

        metadata = {
            "title": title,
            "artist": artist,
            "duration": duration,
            "thumbnail": thumbnail,
            "album": "SoundCloud",
        }
        return file_bytes, metadata

    async def import_track(
        self,
        session: AsyncSession,
        user_id: int,
        url: str,
        bot: Optional[Bot] = None,
    ) -> Tuple[Track, bool]:
        """Скачивает трек из SoundCloud, загружает в Telegram Storage и сохраняет в БД."""
        # 1. Скачиваем аудиофайл
        file_bytes, meta = await asyncio.to_thread(self._sync_download, url)

        # 2. Проверяем дубликат по хэшу
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        existing_track_stmt = select(Track).where(Track.file_hash == file_hash)
        existing_track = (await session.execute(existing_track_stmt)).scalar_one_or_none()

        if existing_track:
            # Трек уже есть, привязываем пользователю
            user_track_stmt = select(UserTrack).where(
                UserTrack.user_id == user_id, UserTrack.track_id == existing_track.id
            )
            user_track = (await session.execute(user_track_stmt)).scalar_one_or_none()
            if not user_track:
                session.add(UserTrack(user_id=user_id, track_id=existing_track.id, is_favorite=False))
                await session.commit()
            return existing_track, False

        # 3. Отправляем в Telegram Storage Channel (бесконечное облако)
        channel_file_id = None
        channel_file_unique_id = None
        target_bot = bot or self.get_bot()

        filename = f"{meta['artist']} - {meta['title']}.mp3"
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (" ", "-", "_", ".")).strip() or "track.mp3"

        if target_bot and settings.STORAGE_CHANNEL_ID:
            try:
                caption = f"☁️ SoundCloud: {meta['artist']} — {meta['title']}\n🔗 {url}"
                channel_msg = await target_bot.send_audio(
                    chat_id=settings.STORAGE_CHANNEL_ID,
                    audio=BufferedInputFile(file_bytes, filename=safe_filename),
                    caption=caption,
                    title=meta["title"],
                    performer=meta["artist"],
                    duration=meta["duration"],
                )
                if channel_msg.audio:
                    channel_file_id = channel_msg.audio.file_id
                    channel_file_unique_id = channel_msg.audio.file_unique_id
            except Exception as e:
                logger.warning(f"Не удалось загрузить аудио в storage channel: {e}")

        # 4. Сохраняем трек через track_service
        track, is_new = await track_service.process_and_save_audio(
            session=session,
            file_bytes=file_bytes,
            filename=safe_filename,
            uploader_id=user_id,
            telegram_file_id=channel_file_id,
            telegram_file_unique_id=channel_file_unique_id,
        )

        # 5. Если у трека нет обложки, но есть thumbnail из SoundCloud - скачаем
        if not track.cover_path and meta.get("thumbnail"):
            try:
                async with aiohttp.ClientSession() as http_sess:
                    async with http_sess.get(meta["thumbnail"], timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            cover_bytes = await resp.read()
                            cover_hash = hashlib.sha256(cover_bytes).hexdigest()
                            cover_filename = f"{cover_hash}.jpg"
                            cover_full_path = settings.COVERS_DIR / cover_filename
                            cover_full_path.write_bytes(cover_bytes)
                            track.cover_path = f"/pic/{cover_filename}"
                            await session.commit()
            except Exception as e:
                logger.warning(f"Не удалось скачать обложку трека: {e}")

        return track, is_new


soundcloud_service = SoundCloudService()
