from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_current_user, get_optional_user
from src.database.session import get_db
from src.models import Track, User
from src.schemas.track import TrackListResponse, TrackResponse, TrackUpdate
from src.services.storage import storage_service
from src.services.track_service import track_service

router = APIRouter(prefix="/tracks", tags=["Треки и Стриминг"])


@router.get("", response_model=TrackListResponse)
async def list_tracks(
    q: Optional[str] = Query(None, description="Поисковый запрос (название, артист, альбом)"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> TrackListResponse:
    """Получение списка треков с поиском и пагинацией."""
    user_id = user.id if user else None
    items, total = await track_service.search_tracks(
        session=db, query=q, user_id=user_id, offset=offset, limit=limit
    )
    return TrackListResponse(items=items, total=total, offset=offset, limit=limit)


@router.get("/{track_id}", response_model=TrackResponse)
async def get_track(
    track_id: int,
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> TrackResponse:
    """Получение детальной информации о треке."""
    stmt = select(Track).where(Track.id == track_id)
    track = (await db.execute(stmt)).scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Трек не найден")

    is_fav = False
    if user:
        from src.models import UserTrack
        fav_stmt = select(UserTrack).where(
            UserTrack.user_id == user.id,
            UserTrack.track_id == track.id,
            UserTrack.is_favorite == True,
        )
        is_fav = (await db.execute(fav_stmt)).scalar_one_or_none() is not None

    return TrackResponse(
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
        is_favorite=is_fav,
        created_at=track.created_at,
    )


@router.get("/{track_id}/stream")
async def stream_track(
    track_id: int,
    range: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Потоковое воспроизведение с поддержкой HTTP Range (206 Partial Content).
    Позволяет браузерному плееру и Mini App перематывать аудио на произвольную секунду.
    """
    stmt = select(Track).where(Track.id == track_id)
    track = (await db.execute(stmt)).scalar_one_or_none()
    if not track:
        await db.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Трек не найден")

    file_path = track.file_path
    telegram_file_id = track.telegram_file_id
    mime_type = track.mime_type
    await db.close()

    if file_path and Path(file_path).exists():
        return storage_service.create_streaming_response(
            file_path=Path(file_path),
            range_header=range,
            mime_type=mime_type,
            as_attachment=False,
        )
    elif telegram_file_id:
        return await storage_service.create_telegram_proxy_streaming_response(
            telegram_file_id=telegram_file_id,
            range_header=range,
            mime_type=mime_type,
            as_attachment=False,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден ни на диске, ни в Telegram",
        )


@router.get("/{track_id}/download")
async def download_track(
    track_id: int,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Скачивание аудиофайла целиком для сохранения в локальное хранилище (IndexedDB)
    в офлайн-режиме Telegram Mini App.
    """
    stmt = select(Track).where(Track.id == track_id)
    track = (await db.execute(stmt)).scalar_one_or_none()
    if not track:
        await db.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Трек не найден")

    safe_filename = f"{track.artist} - {track.title}.mp3".replace("/", "_").replace("\\", "_")
    file_path = track.file_path
    telegram_file_id = track.telegram_file_id
    mime_type = track.mime_type
    await db.close()

    if file_path and Path(file_path).exists():
        return storage_service.create_streaming_response(
            file_path=Path(file_path),
            range_header=None,
            mime_type=mime_type,
            as_attachment=True,
            filename=safe_filename,
        )
    elif telegram_file_id:
        return await storage_service.create_telegram_proxy_streaming_response(
            telegram_file_id=telegram_file_id,
            range_header=None,
            mime_type=mime_type,
            as_attachment=True,
            filename=safe_filename,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден ни на диске, ни в Telegram",
        )


@router.get("/{track_id}/cover")
async def get_track_cover(
    track_id: int,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Возвращает обложку трека, если она была извлечена из ID3-тегов."""
    stmt = select(Track).where(Track.id == track_id)
    track = (await db.execute(stmt)).scalar_one_or_none()
    if not track or not track.cover_path or not Path(track.cover_path).exists():
        await db.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Обложка отсутствует")

    cover_path = track.cover_path
    await db.close()
    return FileResponse(cover_path, media_type="image/jpeg")


@router.post("/{track_id}/favorite")
async def toggle_track_favorite(
    track_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Добавляет или удаляет трек из избранного текущего пользователя."""
    stmt = select(Track).where(Track.id == track_id)
    track = (await db.execute(stmt)).scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Трек не найден")

    new_fav_status = await track_service.toggle_favorite(
        session=db, user_id=user.id, track_id=track.id
    )
    return {"track_id": track_id, "is_favorite": new_fav_status}


@router.patch("/{track_id}", response_model=TrackResponse)
async def update_track_metadata(
    track_id: int,
    payload: TrackUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackResponse:
    """Ручное редактирование названия, артиста или альбома трека."""
    stmt = select(Track).where(Track.id == track_id)
    track = (await db.execute(stmt)).scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Трек не найден")

    # Редактировать может загрузивший пользователь или администратор
    if track.uploader_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав на редактирование этого трека")

    if payload.title is not None and payload.title.strip():
        track.title = payload.title.strip()
    if payload.artist is not None:
        track.artist = payload.artist.strip() or "Unknown Artist"
    if payload.album is not None:
        track.album = payload.album.strip() if payload.album.strip() else None

    await db.commit()
    await db.refresh(track)

    return TrackResponse(
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
        created_at=track.created_at,
    )


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track(
    track_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Полное удаление трека из базы данных и медиатеки."""
    stmt = select(Track).where(Track.id == track_id)
    track = (await db.execute(stmt)).scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Трек не найден")

    # Удалить может загрузивший пользователь, администратор, либо если трек без владельца
    if track.uploader_id and track.uploader_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав на удаление этого трека")

    # Удаляем физические файлы с диска, если остались
    if track.file_path and Path(track.file_path).exists():
        try:
            Path(track.file_path).unlink()
        except Exception:
            pass

    if track.cover_path and Path(track.cover_path).exists():
        try:
            Path(track.cover_path).unlink()
        except Exception:
            pass

    await db.delete(track)
    await db.commit()


@router.post("/{track_id}/toggle-privacy")
async def toggle_track_privacy(
    track_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Переключение статуса приватности трека (публичный / только для себя)."""
    stmt = select(Track).where(Track.id == track_id)
    track = (await db.execute(stmt)).scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Трек не найден")

    if track.uploader_id != user.id and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав на изменение настроек приватности")

    track.is_private = not track.is_private
    await db.commit()
    await db.refresh(track)

    return {"track_id": track.id, "is_private": track.is_private}

