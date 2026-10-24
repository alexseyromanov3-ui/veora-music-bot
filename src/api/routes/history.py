from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_current_user
from src.database.session import get_db
from src.models import User
from src.schemas.history import HistoryRecordCreate
from src.schemas.track import TrackResponse
from src.services.history_service import history_service

router = APIRouter(prefix="/history", tags=["История прослушиваний"])


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def record_listening(
    payload: HistoryRecordCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Фиксация события прослушивания трека."""
    await history_service.record_listen(
        session=db,
        user_id=user.id,
        track_id=payload.track_id,
        duration_played=payload.duration_played,
    )


@router.get("/recently-played", response_model=List[TrackResponse])
async def get_recently_played(
    limit: int = Query(30, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[TrackResponse]:
    """Недавно прослушанные треки текущего пользователя."""
    return await history_service.get_recently_played(
        session=db, user_id=user.id, limit=limit
    )
