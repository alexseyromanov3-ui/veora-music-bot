from typing import Optional
from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.session import get_db
from src.models.user import User
from src.services.auth import auth_service
from src.services.track_service import track_service


async def get_current_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    init_data_query: Optional[str] = Query(None, alias="init_data"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Зависимость авторизации: извлекает и проверяет initData из заголовка или query-параметра.
    Если данные подлинные, получает или создает пользователя в БД.
    """
    init_data = x_telegram_init_data or init_data_query
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствуют данные авторизации Telegram (initData)",
        )

    telegram_user = auth_service.validate_init_data(init_data)
    if not telegram_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительные или просроченные данные авторизации",
        )

    user = await track_service.get_or_create_user(
        session=db,
        user_id=telegram_user.id,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
        username=telegram_user.username,
    )
    return user


async def get_optional_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    init_data_query: Optional[str] = Query(None, alias="init_data"),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Необязательная авторизация для публичных разделов."""
    init_data = x_telegram_init_data or init_data_query
    if not init_data:
        return None

    telegram_user = auth_service.validate_init_data(init_data)
    if not telegram_user:
        return None

    return await track_service.get_or_create_user(
        session=db,
        user_id=telegram_user.id,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
        username=telegram_user.username,
    )
