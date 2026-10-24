from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_current_user
from src.database.session import get_db
from src.models import User
from src.schemas.search import (
    SoundCloudImportRequest,
    SoundCloudImportResponse,
    SoundCloudSearchResponse,
    SoundCloudSearchResult,
)
from src.schemas.track import TrackResponse
from src.services.soundcloud_service import soundcloud_service

router = APIRouter(prefix="/search", tags=["Поиск онлайн музыки"])


@router.get("/soundcloud", response_model=SoundCloudSearchResponse)
async def search_soundcloud(
    q: str = Query(..., min_length=1, max_length=120, description="Поисковый запрос"),
    limit: int = Query(10, ge=1, le=25, description="Лимит результатов"),
    user: User = Depends(get_current_user),
) -> SoundCloudSearchResponse:
    """Поиск треков в SoundCloud."""
    try:
        raw_items = await soundcloud_service.search(query=q, limit=limit)
        items = [SoundCloudSearchResult(**item) for item in raw_items]
        return SoundCloudSearchResponse(query=q, items=items, total=len(items))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка поиска в SoundCloud: {str(e)}",
        )


@router.post("/soundcloud/import", response_model=SoundCloudImportResponse)
async def import_soundcloud_track(
    payload: SoundCloudImportRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SoundCloudImportResponse:
    """Импорт и сохранение трека из SoundCloud в медиатеку пользователя."""
    if not payload.url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL трека не указан")

    try:
        track, is_new = await soundcloud_service.import_track(
            session=db,
            user_id=user.id,
            url=payload.url,
        )
        track_resp = TrackResponse(
            id=track.id,
            title=track.title,
            artist=track.artist,
            album=track.album,
            duration=track.duration,
            bit_rate=track.bit_rate,
            file_size=track.file_size,
            mime_type=track.mime_type,
            file_hash=track.file_hash,
            has_cover=bool(track.cover_path),
            cover_url=f"/api/tracks/{track.id}/cover" if track.cover_path else None,
            stream_url=f"/api/tracks/{track.id}/stream",
            download_url=f"/api/tracks/{track.id}/download",
            is_favorite=False,
            is_private=track.is_private,
            uploader_id=track.uploader_id,
            created_at=track.created_at,
        )
        msg = "Трек успешно добавлен в вашу медиатеку!" if is_new else "Трек уже есть на сервере и добавлен в вашу медиатеку!"
        return SoundCloudImportResponse(success=True, track=track_resp, message=msg)
    except Exception as e:
        return SoundCloudImportResponse(
            success=False,
            track=None,
            message=f"Не удалось загрузить трек из SoundCloud: {str(e)}",
        )
