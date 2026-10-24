from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import ListeningHistory, Track, UserTrack
from src.schemas.history import HistoryItemResponse
from src.schemas.track import TrackResponse


class HistoryService:
    """Сервис аналитики и истории воспроизведения треков."""

    @staticmethod
    async def record_listen(
        session: AsyncSession, user_id: int, track_id: int, duration_played: int = 1
    ) -> None:
        """Фиксирует факт прослушивания трека."""
        record = ListeningHistory(
            user_id=user_id,
            track_id=track_id,
            duration_played=max(1, duration_played),
        )
        session.add(record)
        await session.commit()

    @staticmethod
    async def get_recently_played(
        session: AsyncSession, user_id: int, limit: int = 30
    ) -> List[TrackResponse]:
        """Возвращает уникальные недавно прослушанные треки пользователя."""
        stmt = (
            select(Track)
            .join(ListeningHistory, ListeningHistory.track_id == Track.id)
            .where(ListeningHistory.user_id == user_id)
            .order_by(ListeningHistory.listened_at.desc())
            .limit(limit * 2)  # с запасом для дедупликации
        )
        tracks = (await session.execute(stmt)).scalars().all()

        # Дедупликация с сохранением хронологического порядка
        seen = set()
        unique_tracks = []
        for t in tracks:
            if t.id not in seen:
                seen.add(t.id)
                unique_tracks.append(t)
            if len(unique_tracks) >= limit:
                break

        # Проверка избранного
        fav_ids = set()
        if unique_tracks:
            fav_stmt = select(UserTrack.track_id).where(
                UserTrack.user_id == user_id,
                UserTrack.track_id.in_([t.id for t in unique_tracks]),
                UserTrack.is_favorite == True,
            )
            fav_ids = set((await session.execute(fav_stmt)).scalars().all())

        return [
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
                is_favorite=(t.id in fav_ids),
                created_at=t.created_at,
            )
            for t in unique_tracks
        ]


history_service = HistoryService()
