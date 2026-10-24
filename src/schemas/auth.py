from typing import Optional
from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_admin: bool = False


class AuthInitDataRequest(BaseModel):
    init_data: str


class AuthResponse(BaseModel):
    success: bool
    user: UserResponse
    message: Optional[str] = None
