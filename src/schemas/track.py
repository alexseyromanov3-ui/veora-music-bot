from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TrackBase(BaseModel):
    title: str
    artist: str
    album: Optional[str] = None
    duration: int
    bit_rate: Optional[int] = None
    file_size: int
    mime_type: str = "audio/mpeg"


class TrackResponse(TrackBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_hash: str
    has_cover: bool = False
    stream_url: str
    cover_url: Optional[str] = None
    download_url: str
    is_favorite: bool = False
    is_private: bool = False
    uploader_id: Optional[int] = None
    uploader_name: Optional[str] = None
    created_at: datetime


class TrackListResponse(BaseModel):
    items: List[TrackResponse]
    total: int
    offset: int
    limit: int


class TrackUpdate(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
