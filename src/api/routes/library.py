from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_current_user, get_optional_user
from src.database.session import get_db
from src.models import Track, User, UserTrack
from src.schemas.track import TrackListResponse, TrackResponse

router = APIRouter(prefix="/library", tags=["Библиотека пользователя"])


@router.get("/tracks", response_model=TrackListResponse)
async def get_my_library(
    favorites_only: bool = Query(False, description="Только избранные треки"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> TrackListResponse:
    """Возвращает персональную библиотеку треков текущего пользователя."""
    if not user:
        await db.close()
        return TrackListResponse(items=[], total=0, offset=offset, limit=limit)

    stmt = (
        select(Track, UserTrack.is_favorite)
        .join(UserTrack, UserTrack.track_id == Track.id)
        .where(UserTrack.user_id == user.id)
    )

    if favorites_only:
        stmt = stmt.where(UserTrack.is_favorite == True)

    count_stmt = (
        select(func.count(Track.id))
        .join(UserTrack, UserTrack.track_id == Track.id)
        .where(UserTrack.user_id == user.id)
    )
    if favorites_only:
        count_stmt = count_stmt.where(UserTrack.is_favorite == True)

    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(UserTrack.added_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(stmt)).all()

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
            is_favorite=is_fav,
            created_at=t.created_at,
        )
        for t, is_fav in rows
    ]

    await db.close()
    return TrackListResponse(items=items, total=total, offset=offset, limit=limit)


@router.delete("/tracks/{track_id}", status_code=204)
async def remove_track_from_my_library(
    track_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Удаляет трек из персональной медиатеки текущего пользователя."""
    stmt = select(UserTrack).where(
        UserTrack.user_id == user.id, UserTrack.track_id == track_id
    )
    link = (await db.execute(stmt)).scalar_one_or_none()
    if link:
        await db.delete(link)
        await db.commit()

