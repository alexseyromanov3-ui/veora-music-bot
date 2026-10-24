from typing import List, Optional
from pydantic import BaseModel
from src.schemas.track import TrackResponse


class SoundCloudSearchResult(BaseModel):
    id: str
    title: str
    artist: str
    duration: int
    thumbnail: Optional[str] = None
    url: str
    source: str = "soundcloud"


class SoundCloudSearchResponse(BaseModel):
    query: str
    items: List[SoundCloudSearchResult]
    total: int


class SoundCloudImportRequest(BaseModel):
    url: str
    title: Optional[str] = None
    artist: Optional[str] = None
    thumbnail: Optional[str] = None


class SoundCloudImportResponse(BaseModel):
    success: bool
    track: Optional[TrackResponse] = None
    message: str
