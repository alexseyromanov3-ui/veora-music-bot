from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class FriendConnectRequest(BaseModel):
    friend_id: Optional[int] = None
    query: Optional[str] = None


class FriendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    tracks_count: int = 0
    connected_at: datetime
