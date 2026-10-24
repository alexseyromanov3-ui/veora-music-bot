from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Track, User, UserFriend, UserTrack
from src.schemas.social import FriendResponse
from src.schemas.track import TrackResponse


class FriendService:
    """Сервис управления социальными связями и музыкой друзей."""

    @staticmethod
    async def connect_friends(
        session: AsyncSession, user_id: int, friend_id: int
    ) -> bool:
        """Создает взаимную дружбу между двумя пользователями."""
        success, _, _ = await FriendService.connect_friends_flexible(
            session=session, user_id=user_id, friend_id=friend_id
        )
        return success

    @staticmethod
    async def connect_friends_flexible(
        session: AsyncSession,
        user_id: int,
        friend_id: Optional[int] = None,
        query: Optional[str] = None,
    ) -> Tuple[bool, Optional[User], str]:
        """Универсальное взаимное добавление в друзья по ID или username."""
        target_friend = None

        if friend_id:
            if friend_id == user_id:
                return False, None, "Нельзя добавить самого себя в друзья"
            friend_stmt = select(User).where(User.id == friend_id)
            target_friend = (await session.execute(friend_stmt)).scalar_one_or_none()

        if not target_friend and query:
            clean_q = str(query).strip().lstrip("@")
            if clean_q.isdigit():
                fid = int(clean_q)
                if fid == user_id:
                    return False, None, "Нельзя добавить самого себя в друзья"
                friend_stmt = select(User).where(User.id == fid)
                target_friend = (await session.execute(friend_stmt)).scalar_one_or_none()
            else:
                friend_stmt = select(User).where(func.lower(User.username) == clean_q.lower())
                target_friend = (await session.execute(friend_stmt)).scalar_one_or_none()

        if not target_friend:
            return False, None, "Пользователь не найден в боте. Убедитесь, что друг хотя бы раз открыл бота"

        if target_friend.id == user_id:
            return False, None, "Нельзя добавить самого себя в друзья"

        f_id = target_friend.id
        link1 = (
            await session.execute(
                select(UserFriend).where(
                    UserFriend.user_id == user_id, UserFriend.friend_id == f_id
                )
            )
        ).scalar_one_or_none()

        if not link1:
            session.add(UserFriend(user_id=user_id, friend_id=f_id))

        link2 = (
            await session.execute(
                select(UserFriend).where(
                    UserFriend.user_id == f_id, UserFriend.friend_id == user_id
                )
            )
        ).scalar_one_or_none()

        if not link2:
            session.add(UserFriend(user_id=f_id, friend_id=user_id))

        await session.commit()
        return True, target_friend, f"Пользователь {target_friend.first_name} успешно добавлен в друзья!"

    @staticmethod
    async def get_user_friends(
        session: AsyncSession, user_id: int
    ) -> List[FriendResponse]:
        """Возвращает список друзей с подсчетом загруженных ими треков."""
        stmt = (
            select(
                User,
                UserFriend.created_at.label("connected_at"),
                func.count(Track.id).label("tracks_count"),
            )
            .join(UserFriend, UserFriend.friend_id == User.id)
            .outerjoin(
                Track,
                (Track.uploader_id == User.id) & (Track.is_private == False),
            )
            .where(UserFriend.user_id == user_id)
            .group_by(User.id, UserFriend.created_at)
            .order_by(UserFriend.created_at.desc())
        )
        rows = (await session.execute(stmt)).all()

        return [
            FriendResponse(
                id=u.id,
                first_name=u.first_name,
                last_name=u.last_name,
                username=u.username,
                tracks_count=count,
                connected_at=conn_at,
            )
            for u, conn_at, count in rows
        ]

    @staticmethod
    async def get_friends_tracks(
        session: AsyncSession, user_id: int, offset: int = 0, limit: int = 50
    ) -> Tuple[List[TrackResponse], int]:
        """Возвращает треки, загруженные друзьями пользователя."""
        # Находим ID друзей
        friends_subquery = (
            select(UserFriend.friend_id).where(UserFriend.user_id == user_id).scalar_subquery()
        )

        base_stmt = (
            select(Track, User.first_name, User.username)
            .outerjoin(User, User.id == Track.uploader_id)
            .where(
                Track.uploader_id.in_(friends_subquery),
                Track.is_private == False,
            )
        )

        count_stmt = (
            select(func.count(Track.id)).where(
                Track.uploader_id.in_(friends_subquery),
                Track.is_private == False,
            )
        )
        total = (await session.execute(count_stmt)).scalar_one()

        tracks_stmt = base_stmt.order_by(Track.created_at.desc()).offset(offset).limit(limit)
        rows = (await session.execute(tracks_stmt)).all()

        # Проверка избранного
        fav_ids = set()
        if rows:
            track_ids = [t.id for t, _, _ in rows]
            fav_stmt = select(UserTrack.track_id).where(
                UserTrack.user_id == user_id,
                UserTrack.track_id.in_(track_ids),
                UserTrack.is_favorite == True,
            )
            fav_ids = set((await session.execute(fav_stmt)).scalars().all())

        items = [
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
                is_private=t.is_private,
                uploader_id=t.uploader_id,
                uploader_name=f"@{u_name}" if u_name else (f_name or "Друг"),
                created_at=t.created_at,
            )
            for t, f_name, u_name in rows
        ]

        return items, total

    @staticmethod
    async def remove_friend(
        session: AsyncSession, user_id: int, friend_id: int
    ) -> None:
        """Удаляет взаимную дружбу."""
        stmt = select(UserFriend).where(
            or_(
                (UserFriend.user_id == user_id) & (UserFriend.friend_id == friend_id),
                (UserFriend.user_id == friend_id) & (UserFriend.friend_id == user_id),
            )
        )
        links = (await session.execute(stmt)).scalars().all()
        for link in links:
            await session.delete(link)
        await session.commit()


friend_service = FriendService()
