from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_current_user, get_optional_user
from src.database.session import get_db
from src.models import Track, User, UserTrack
from src.schemas.social import FriendConnectRequest, FriendResponse
from src.schemas.track import TrackListResponse, TrackResponse
from src.services.friend_service import friend_service
from src.services.recommendation_service import recommendation_service

router = APIRouter(prefix="/social", tags=["Социальные функции и Рекомендации"])


async def _notify_friend_telegram(target_friend_id: int, user_name: str, user_username: Optional[str] = None) -> None:
    """Фоновое уведомление в Telegram о взаимном добавлении в друзья."""
    try:
        import aiohttp
        from src.config import settings
        if settings.BOT_TOKEN in ("MOCK_TOKEN", ""):
            return
        handle = f" (@{user_username})" if user_username else ""
        text = (
            f"🎉 **У вас новый друг в VEORA Music!**\n\n"
            f"**{user_name}**{handle} добавил вас в друзья!\n"
            f"Теперь вы можете слушать музыку друг друга во вкладке **«Друзья 👥»**."
        )
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": target_friend_id,
                "text": text,
                "parse_mode": "Markdown",
            }
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=4)):
                pass
    except Exception:
        pass


@router.post("/friends/connect", status_code=status.HTTP_200_OK)
async def connect_friend(
    payload: FriendConnectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Взаимное добавление в друзья по ID или username."""
    success, friend_obj, message = await friend_service.connect_friends_flexible(
        session=db, user_id=user.id, friend_id=payload.friend_id, query=payload.query
    )
    if success and friend_obj:
        import asyncio
        asyncio.create_task(_notify_friend_telegram(friend_obj.id, user.first_name, user.username))

    return {
        "success": success,
        "friend_id": friend_obj.id if friend_obj else payload.friend_id,
        "friend_name": friend_obj.first_name if friend_obj else None,
        "message": message,
    }


@router.get("/friends", response_model=List[FriendResponse])
async def list_friends(
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> List[FriendResponse]:
    """Список друзей текущего пользователя."""
    if not user:
        await db.close()
        return []
    res = await friend_service.get_user_friends(session=db, user_id=user.id)
    await db.close()
    return res


@router.get("/friends/tracks", response_model=TrackListResponse)
async def list_friends_tracks(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> TrackListResponse:
    """Треки, загруженные друзьями пользователя."""
    if not user:
        await db.close()
        return TrackListResponse(items=[], total=0, offset=offset, limit=limit)
    items, total = await friend_service.get_friends_tracks(
        session=db, user_id=user.id, offset=offset, limit=limit
    )
    await db.close()
    return TrackListResponse(items=items, total=total, offset=offset, limit=limit)


@router.delete("/friends/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_friend(
    friend_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Удаление из друзей."""
    await friend_service.remove_friend(
        session=db, user_id=user.id, friend_id=friend_id
    )


@router.get("/community", response_model=TrackListResponse)
async def list_community_feed(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> TrackListResponse:
    """Общая лента сообщества: публичные треки от всех пользователей."""
    public_filter = or_(Track.is_private == False, Track.is_private.is_(None))
    base_stmt = (
        select(Track, User.first_name, User.username)
        .outerjoin(User, User.id == Track.uploader_id)
        .where(public_filter)
    )

    count_stmt = select(func.count(Track.id)).where(public_filter)
    total = (await db.execute(count_stmt)).scalar_one()

    tracks_stmt = base_stmt.order_by(Track.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(tracks_stmt)).all()

    # Проверка избранного
    fav_ids = set()
    if rows and user:
        track_ids = [t.id for t, _, _ in rows]
        fav_stmt = select(UserTrack.track_id).where(
            UserTrack.user_id == user.id,
            UserTrack.track_id.in_(track_ids),
            UserTrack.is_favorite == True,
        )
        fav_ids = set((await db.execute(fav_stmt)).scalars().all())

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
            is_private=t.is_private or False,
            uploader_id=t.uploader_id,
            uploader_name=f"@{u_name}" if u_name else (f_name or "Сообщество"),
            created_at=t.created_at,
        )
        for t, f_name, u_name in rows
    ]

    await db.close()
    return TrackListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/recommendations", response_model=List[TrackResponse])
async def get_smart_recommendations(
    limit: int = Query(25, ge=1, le=50),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> List[TrackResponse]:
    """Персональные рекомендации «Для вас» на основе музыкального вкуса."""
    if not user:
        feed = await list_community_feed(offset=0, limit=limit, user=None, db=db)
        return feed.items

    result = await recommendation_service.get_recommendations_for_user(
        session=db, user_id=user.id, limit=limit
    )
    await db.close()
    return result
