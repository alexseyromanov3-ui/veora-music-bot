from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Playlist, PlaylistTrack, Track, UserTrack
from src.schemas.playlist import PlaylistDetailResponse, PlaylistResponse
from src.schemas.track import TrackResponse


class PlaylistService:
    """Сервис для управления плейлистами пользователей."""

    @staticmethod
    async def create_playlist(
        session: AsyncSession,
        user_id: int,
        title: str,
        description: Optional[str] = None,
        is_public: bool = False,
    ) -> PlaylistResponse:
        playlist = Playlist(
            user_id=user_id,
            title=title.strip(),
            description=description.strip() if description else None,
            is_public=is_public,
        )
        session.add(playlist)
        await session.commit()
        await session.refresh(playlist)

        return PlaylistResponse(
            id=playlist.id,
            user_id=playlist.user_id,
            title=playlist.title,
            description=playlist.description,
            is_public=playlist.is_public,
            tracks_count=0,
            created_at=playlist.created_at,
            updated_at=playlist.updated_at,
        )

    @staticmethod
    async def get_user_playlists(
        session: AsyncSession, user_id: int
    ) -> List[PlaylistResponse]:
        # Получаем плейлисты пользователя с подсчетом треков
        stmt = (
            select(Playlist, func.count(PlaylistTrack.track_id).label("tracks_count"))
            .outerjoin(PlaylistTrack, Playlist.id == PlaylistTrack.playlist_id)
            .where(Playlist.user_id == user_id)
            .group_by(Playlist.id)
            .order_by(Playlist.updated_at.desc())
        )
        rows = (await session.execute(stmt)).all()

        return [
            PlaylistResponse(
                id=p.id,
                user_id=p.user_id,
                title=p.title,
                description=p.description,
                is_public=p.is_public,
                tracks_count=count,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p, count in rows
        ]

    @staticmethod
    async def get_playlist_detail(
        session: AsyncSession, playlist_id: int, current_user_id: int
    ) -> PlaylistDetailResponse:
        stmt = select(Playlist).where(Playlist.id == playlist_id)
        playlist = (await session.execute(stmt)).scalar_one_or_none()
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Плейлист не найден"
            )

        if not playlist.is_public and playlist.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Доступ ограничен"
            )

        # Загрузка треков плейлиста
        tracks_stmt = (
            select(Track, PlaylistTrack.position)
            .join(PlaylistTrack, PlaylistTrack.track_id == Track.id)
            .where(PlaylistTrack.playlist_id == playlist_id)
            .order_by(PlaylistTrack.position.asc(), PlaylistTrack.added_at.asc())
        )
        track_rows = (await session.execute(tracks_stmt)).all()

        # Проверка избранного
        fav_track_ids = set()
        if track_rows:
            track_ids = [t.id for t, _ in track_rows]
            fav_stmt = select(UserTrack.track_id).where(
                UserTrack.user_id == current_user_id,
                UserTrack.track_id.in_(track_ids),
                UserTrack.is_favorite == True,
            )
            fav_track_ids = set((await session.execute(fav_stmt)).scalars().all())

        track_responses = [
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
                is_favorite=(t.id in fav_track_ids),
                created_at=t.created_at,
            )
            for t, _ in track_rows
        ]

        return PlaylistDetailResponse(
            id=playlist.id,
            user_id=playlist.user_id,
            title=playlist.title,
            description=playlist.description,
            is_public=playlist.is_public,
            tracks_count=len(track_responses),
            tracks=track_responses,
            created_at=playlist.created_at,
            updated_at=playlist.updated_at,
        )

    @staticmethod
    async def add_track(
        session: AsyncSession,
        playlist_id: int,
        user_id: int,
        track_id: int,
        position: Optional[int] = None,
    ) -> None:
        stmt = select(Playlist).where(
            Playlist.id == playlist_id, Playlist.user_id == user_id
        )
        playlist = (await session.execute(stmt)).scalar_one_or_none()
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Плейлист не найден или нет прав доступа",
            )

        # Проверяем наличие трека
        track_stmt = select(Track).where(Track.id == track_id)
        if not (await session.execute(track_stmt)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Трек не найден"
            )

        # Проверяем, есть ли уже этот трек в плейлисте
        link_stmt = select(PlaylistTrack).where(
            PlaylistTrack.playlist_id == playlist_id,
            PlaylistTrack.track_id == track_id,
        )
        existing = (await session.execute(link_stmt)).scalar_one_or_none()
        if existing:
            return  # Уже в плейлисте

        if position is None:
            max_pos_stmt = select(func.coalesce(func.max(PlaylistTrack.position), 0)).where(
                PlaylistTrack.playlist_id == playlist_id
            )
            max_pos = (await session.execute(max_pos_stmt)).scalar_one()
            position = max_pos + 1

        new_link = PlaylistTrack(
            playlist_id=playlist_id, track_id=track_id, position=position
        )
        session.add(new_link)
        await session.commit()

    @staticmethod
    async def remove_track(
        session: AsyncSession, playlist_id: int, user_id: int, track_id: int
    ) -> None:
        stmt = select(Playlist).where(
            Playlist.id == playlist_id, Playlist.user_id == user_id
        )
        playlist = (await session.execute(stmt)).scalar_one_or_none()
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Плейлист не найден или нет прав доступа",
            )

        link_stmt = select(PlaylistTrack).where(
            PlaylistTrack.playlist_id == playlist_id,
            PlaylistTrack.track_id == track_id,
        )
        link = (await session.execute(link_stmt)).scalar_one_or_none()
        if link:
            await session.delete(link)
            await session.commit()

    @staticmethod
    async def delete_playlist(
        session: AsyncSession, playlist_id: int, user_id: int
    ) -> None:
        stmt = select(Playlist).where(
            Playlist.id == playlist_id, Playlist.user_id == user_id
        )
        playlist = (await session.execute(stmt)).scalar_one_or_none()
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Плейлист не найден или нет прав доступа",
            )

        await session.delete(playlist)
        await session.commit()


playlist_service = PlaylistService()
