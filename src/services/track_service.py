import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.models import Track, User, UserTrack
from src.services.audio_metadata import AudioMetadataService
from src.services.storage import storage_service
from src.schemas.track import TrackResponse


class TrackService:
    """Сервис управления аудиотреками и медиатекой."""

    @staticmethod
    async def get_or_create_user(
        session: AsyncSession,
        user_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
    ) -> User:
        """Получает существующего пользователя или создает нового."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                id=user_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            # Обновляем профиль при изменениях в Telegram
            updated = False
            if user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if user.username != username:
                user.username = username
                updated = True
            if updated:
                await session.commit()
                await session.refresh(user)

        return user

    @staticmethod
    async def process_and_save_audio(
        session: AsyncSession,
        file_bytes: bytes,
        filename: str,
        uploader_id: int,
        telegram_file_id: Optional[str] = None,
        telegram_file_unique_id: Optional[str] = None,
    ) -> Tuple[Track, bool]:
        """
        Обрабатывает аудиофайл:
        1. Временное сохранение для анализа через mutagen.
        2. Извлечение тегов и расчет SHA-256 хеша.
        3. Проверка на дубликаты: если трек уже существует, связывает его с пользователем.
        4. Если трек новый — переносит аудио в хранилище, сохраняет обложку и создает запись в БД.
        Возвращает: (Track, is_new: bool)
        """
        # Создаем временный файл для чтения тегов
        temp_dir = settings.MEDIA_DIR / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            dir=temp_dir, delete=False, suffix=".mp3"
        ) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)

        try:
            metadata = AudioMetadataService.extract_metadata(
                tmp_path, fallback_filename=filename
            )

            # Проверяем наличие по sha256 хешу
            stmt = select(Track).where(Track.file_hash == metadata.file_hash)
            existing = (await session.execute(stmt)).scalar_one_or_none()

            if existing:
                # Трек уже есть на сервере! Добавляем в персональную библиотеку загрузившего
                await TrackService.add_to_user_library(
                    session, user_id=uploader_id, track_id=existing.id
                )
                return existing, False

            # Если включено локальное сохранение - сохраняем mp3 на диск,
            # иначе храним только в Telegram-канале (0 байт на диске!)
            final_audio_path_str = ""
            if settings.SAVE_LOCAL_AUDIO:
                final_audio_path = await storage_service.save_audio(
                    metadata.file_hash, file_bytes
                )
                final_audio_path_str = str(final_audio_path)

            # Сохраняем обложку, если найдена в тегах
            cover_path_str: Optional[str] = None
            if metadata.cover_bytes:
                cover_path = await storage_service.save_cover(
                    metadata.file_hash, metadata.cover_bytes
                )
                cover_path_str = str(cover_path)

            track = Track(
                file_hash=metadata.file_hash,
                title=metadata.title,
                artist=metadata.artist,
                album=metadata.album,
                duration=metadata.duration,
                bit_rate=metadata.bit_rate,
                file_size=metadata.file_size,
                file_path=final_audio_path_str,
                cover_path=cover_path_str,
                mime_type=metadata.mime_type,
                telegram_file_id=telegram_file_id,
                telegram_file_unique_id=telegram_file_unique_id,
                uploader_id=uploader_id,
            )
            session.add(track)
            await session.commit()
            await session.refresh(track)

            # Добавляем в библиотеку пользователя
            await TrackService.add_to_user_library(
                session, user_id=uploader_id, track_id=track.id
            )

            return track, True

        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

    @staticmethod
    async def add_to_user_library(
        session: AsyncSession, user_id: int, track_id: int
    ) -> None:
        """Добавляет трек в библиотеку пользователя, если его там еще нет."""
        stmt = select(UserTrack).where(
            UserTrack.user_id == user_id, UserTrack.track_id == track_id
        )
        existing_link = (await session.execute(stmt)).scalar_one_or_none()
        if not existing_link:
            new_link = UserTrack(user_id=user_id, track_id=track_id)
            session.add(new_link)
            await session.commit()

    @staticmethod
    async def toggle_favorite(
        session: AsyncSession, user_id: int, track_id: int
    ) -> bool:
        """Переключает статус 'В избранном'. Возвращает новый статус."""
        stmt = select(UserTrack).where(
            UserTrack.user_id == user_id, UserTrack.track_id == track_id
        )
        link = (await session.execute(stmt)).scalar_one_or_none()
        if not link:
            link = UserTrack(user_id=user_id, track_id=track_id, is_favorite=True)
            session.add(link)
            new_status = True
        else:
            link.is_favorite = not link.is_favorite
            new_status = link.is_favorite

        await session.commit()
        return new_status

    @staticmethod
    async def search_tracks(
        session: AsyncSession,
        query: Optional[str] = None,
        user_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[TrackResponse], int]:
        """Поиск треков по названию, артисту или альбому с пагинацией."""
        stmt = select(Track)
        count_stmt = select(func.count(Track.id))

        if query:
            clean_query = f"%{query.strip()}%"
            filter_cond = or_(
                Track.title.ilike(clean_query),
                Track.artist.ilike(clean_query),
                Track.album.ilike(clean_query),
            )
            stmt = stmt.where(filter_cond)
            count_stmt = count_stmt.where(filter_cond)

        total_res = await session.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = stmt.order_by(Track.created_at.desc()).offset(offset).limit(limit)
        tracks = (await session.execute(stmt)).scalars().all()

        # Проверка статуса избранного для пользователя
        favorite_track_ids = set()
        if user_id and tracks:
            track_ids = [t.id for t in tracks]
            fav_stmt = select(UserTrack.track_id).where(
                UserTrack.user_id == user_id,
                UserTrack.track_id.in_(track_ids),
                UserTrack.is_favorite == True,
            )
            fav_res = await session.execute(fav_stmt)
            favorite_track_ids = set(fav_res.scalars().all())

        results = [
            TrackResponse(
                id=t.id,
                title=t.title,
                artist=t.artist,
                album=t.album,
                duration=t.duration,
                bit_rate=t.bit_rate,
                file_size=t.file_size,
                mime_type=t.mime_type,
                file_hash=t.file_hash,
                has_cover=bool(t.cover_path),
                cover_url=f"/api/tracks/{t.id}/cover" if t.cover_path else None,
                stream_url=f"/api/tracks/{t.id}/stream",
                download_url=f"/api/tracks/{t.id}/download",
                is_favorite=(t.id in favorite_track_ids),
                created_at=t.created_at,
            )
            for t in tracks
        ]

        return results, total


track_service = TrackService()
