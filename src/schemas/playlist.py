from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from src.schemas.track import TrackResponse


class PlaylistCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_public: bool = False


class PlaylistUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_public: Optional[bool] = None


class PlaylistTrackAdd(BaseModel):
    track_id: int
    position: Optional[int] = None


class PlaylistResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    is_public: bool
    tracks_count: int = 0
    created_at: datetime
    updated_at: datetime


class PlaylistDetailResponse(PlaylistResponse):
    tracks: List[TrackResponse] = []
