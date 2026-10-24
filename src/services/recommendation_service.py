from typing import List, Set
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import ListeningHistory, Track, User, UserTrack
from src.schemas.track import TrackResponse


class RecommendationService:
    """Умный алгоритм рекомендаций на основе предпочтений и вкусов пользователя."""

    @staticmethod
    async def get_recommendations_for_user(
        session: AsyncSession, user_id: int, limit: int = 25
    ) -> List[TrackResponse]:
        """
        Формирует персональный список рекомендаций:
        1. Извлекает любимых артистов из избранного и истории.
        2. Ищет публичные треки тех же исполнителей от других пользователей.
        3. Ищет треки пользователей со схожими музыкальными вкусами (коллаборативная фильтрация).
        4. Если истории мало — дополняет популярными новинками сообщества.
        """
        # ID треков, которые уже есть у пользователя в библиотеке
        user_tracks_stmt = select(UserTrack.track_id).where(UserTrack.user_id == user_id)
        existing_track_ids: Set[int] = set(
            (await session.execute(user_tracks_stmt)).scalars().all()
        )

        # 1. Извлекаем любимых артистов пользователя
        fav_artists_stmt = (
            select(Track.artist, func.count(Track.id).label("weight"))
            .join(UserTrack, UserTrack.track_id == Track.id)
            .where(UserTrack.user_id == user_id)
            .group_by(Track.artist)
            .order_by(func.count(Track.id).desc())
            .limit(10)
        )
        fav_artist_rows = (await session.execute(fav_artists_stmt)).all()
        top_artists = [artist for artist, _ in fav_artist_rows if artist and artist != "Unknown Artist"]

        recommended_tracks: List[Track] = []
        collected_ids: Set[int] = set()

        # 2. Поиск треков тех же артистов, которых нет в библиотеке пользователя
        if top_artists:
            artist_filters = [Track.artist.ilike(f"%{a}%") for a in top_artists]
            artist_stmt = (
                select(Track)
                .where(
                    or_(*artist_filters),
                    Track.is_private == False,
                    Track.id.not_in(existing_track_ids) if existing_track_ids else True,
                )
                .order_by(Track.created_at.desc())
                .limit(limit)
            )
            artist_matches = (await session.execute(artist_stmt)).scalars().all()
            for t in artist_matches:
                if t.id not in collected_ids:
                    collected_ids.add(t.id)
                    recommended_tracks.append(t)

        # 3. Коллаборативная фильтрация: треки пользователей с похожими вкусами
        if top_artists and len(recommended_tracks) < limit:
            similar_users_stmt = (
                select(Track.uploader_id)
                .where(
                    Track.artist.in_(top_artists),
                    Track.uploader_id != user_id,
                    Track.uploader_id.is_not(None),
                )
                .distinct()
                .limit(5)
            )
            similar_user_ids = (await session.execute(similar_users_stmt)).scalars().all()

            if similar_user_ids:
                collab_stmt = (
                    select(Track)
                    .where(
                        Track.uploader_id.in_(similar_user_ids),
                        Track.is_private == False,
                        Track.id.not_in(existing_track_ids | collected_ids)
                        if (existing_track_ids | collected_ids)
                        else True,
                    )
                    .order_by(Track.created_at.desc())
                    .limit(limit - len(recommended_tracks))
                )
                collab_matches = (await session.execute(collab_stmt)).scalars().all()
                for t in collab_matches:
                    if t.id not in collected_ids:
                        collected_ids.add(t.id)
                        recommended_tracks.append(t)

        # 4. Fallback: если рекомендаций мало, дополняем треками из ленты сообщества
        if len(recommended_tracks) < limit:
            community_stmt = (
                select(Track)
                .where(
                    Track.is_private == False,
                    Track.id.not_in(existing_track_ids | collected_ids)
                    if (existing_track_ids | collected_ids)
                    else True,
                )
                .order_by(Track.created_at.desc())
                .limit(limit - len(recommended_tracks))
            )
            community_tracks = (await session.execute(community_stmt)).scalars().all()
            for t in community_tracks:
                if t.id not in collected_ids:
                    collected_ids.add(t.id)
                    recommended_tracks.append(t)

        # Подгружаем имена загрузивших пользователей
        uploader_ids = [t.uploader_id for t in recommended_tracks if t.uploader_id]
        user_map = {}
        if uploader_ids:
            users_stmt = select(User).where(User.id.in_(uploader_ids))
            users = (await session.execute(users_stmt)).scalars().all()
            user_map = {
                u.id: (f"@{u.username}" if u.username else u.first_name)
                for u in users
            }

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
                is_favorite=False,
                is_private=t.is_private,
                uploader_id=t.uploader_id,
                uploader_name=user_map.get(t.uploader_id, "Сообщество"),
                created_at=t.created_at,
            )
            for t in recommended_tracks
        ]


recommendation_service = RecommendationService()
