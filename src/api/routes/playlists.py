from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_current_user
from src.database.session import get_db
from src.models import User
from src.schemas.playlist import (
    PlaylistCreate,
    PlaylistDetailResponse,
    PlaylistResponse,
    PlaylistTrackAdd,
    PlaylistUpdate,
)
from src.services.playlist_service import playlist_service

router = APIRouter(prefix="/playlists", tags=["Плейлисты"])


@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    payload: PlaylistCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaylistResponse:
    """Создание нового плейлиста."""
    return await playlist_service.create_playlist(
        session=db,
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        is_public=payload.is_public,
    )


@router.get("", response_model=List[PlaylistResponse])
async def list_my_playlists(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PlaylistResponse]:
    """Список плейлистов текущего пользователя."""
    return await playlist_service.get_user_playlists(session=db, user_id=user.id)


@router.get("/{playlist_id}", response_model=PlaylistDetailResponse)
async def get_playlist(
    playlist_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlaylistDetailResponse:
    """Получение плейлиста с упорядоченным списком треков."""
    return await playlist_service.get_playlist_detail(
        session=db, playlist_id=playlist_id, current_user_id=user.id
    )


@router.post("/{playlist_id}/tracks", status_code=status.HTTP_204_NO_CONTENT)
async def add_track_to_playlist(
    playlist_id: int,
    payload: PlaylistTrackAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Добавление трека в плейлист."""
    await playlist_service.add_track(
        session=db,
        playlist_id=playlist_id,
        user_id=user.id,
        track_id=payload.track_id,
        position=payload.position,
    )


@router.delete("/{playlist_id}/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_track_from_playlist(
    playlist_id: int,
    track_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Удаление трека из плейлиста."""
    await playlist_service.remove_track(
        session=db, playlist_id=playlist_id, user_id=user.id, track_id=track_id
    )


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Удаление плейлиста."""
    await playlist_service.delete_playlist(
        session=db, playlist_id=playlist_id, user_id=user.id
    )
