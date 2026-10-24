from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_current_user
from src.database.session import get_db
from src.models.user import User
from src.schemas.auth import AuthInitDataRequest, AuthResponse, UserResponse
from src.services.auth import auth_service
from src.services.track_service import track_service

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post("/validate", response_model=AuthResponse)
async def validate_init_data(
    payload: AuthInitDataRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Проверяет initData и возвращает профиль пользователя."""
    telegram_user = auth_service.validate_init_data(payload.init_data)
    if not telegram_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректная подпись Telegram initData",
        )

    user = await track_service.get_or_create_user(
        session=db,
        user_id=telegram_user.id,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
        username=telegram_user.username,
    )

    return AuthResponse(
        success=True,
        user=UserResponse(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            is_admin=user.is_admin,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Возвращает текущего авторизованного пользователя."""
    return UserResponse(
        id=current_user.id,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        username=current_user.username,
        is_admin=current_user.is_admin,
    )
