from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from src.schemas.track import TrackResponse


class HistoryRecordCreate(BaseModel):
    track_id: int
    duration_played: int = Field(ge=0, description="Количество прослушанных секунд")


class HistoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    track: TrackResponse
    duration_played: int
    listened_at: datetime
