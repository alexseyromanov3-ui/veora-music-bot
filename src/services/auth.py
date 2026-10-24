import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, unquote
from pydantic import BaseModel
from src.config import settings


class TelegramUserData(BaseModel):
    """Данные пользователя, полученные из initData Telegram WebApp."""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = False


class AuthService:
    """Сервис авторизации и проверки подлинности Telegram WebApp initData."""

    @staticmethod
    def validate_init_data(
        init_data_raw: str,
        bot_token: str = settings.BOT_TOKEN,
        ttl_seconds: int = settings.INIT_DATA_TTL_SECONDS,
    ) -> Optional[TelegramUserData]:
        """
        Проверяет подпись initData по официальному протоколу Telegram:
        1. Извлекается параметр hash.
        2. Формируется data_check_string из остальных параметров в алфавитном порядке.
        3. Вычисляется HMAC-SHA256(secret_key=HMAC_SHA256("WebAppData", bot_token), data_check_string).
        4. Проверяется соответствие хешей и срок жизни auth_date.
        """
        if not init_data_raw:
            return None

        # В режиме разработки/тестов можно разрешить тестовые данные
        if (bot_token == "MOCK_TOKEN" or settings.DEBUG) and "mock_user_id" in init_data_raw:
            mock_id = 999999
            try:
                for part in init_data_raw.split('&'):
                    if part.startswith('mock_user_id='):
                        mock_id = int(part.split('=')[1])
            except Exception:
                pass
            return TelegramUserData(
                id=mock_id,
                first_name="Local Tester",
                username="tester"
            )

        try:
            parsed_data = dict(parse_qsl(init_data_raw, keep_blank_values=True))
            received_hash = parsed_data.pop("hash", None)
            if not received_hash:
                return None

            # Проверка auth_date
            auth_date_str = parsed_data.get("auth_date")
            if not auth_date_str:
                return None

            auth_date = int(auth_date_str)
            current_time = int(time.time())
            if current_time - auth_date > ttl_seconds:
                # Срок действия авторизации истек
                return None

            # Формирование data_check_string
            data_check_list = [f"{k}={v}" for k, v in sorted(parsed_data.items())]
            data_check_string = "\n".join(data_check_list)

            # Вычисление секретного ключа
            secret_key = hmac.new(
                b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
            ).digest()

            # Вычисление проверочного хеша
            calculated_hash = hmac.new(
                secret_key, data_check_string.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(calculated_hash, received_hash):
                return None

            # Извлечение данных пользователя
            user_json_str = parsed_data.get("user")
            if not user_json_str:
                return None

            user_dict = json.loads(user_json_str)
            return TelegramUserData(
                id=user_dict["id"],
                first_name=user_dict.get("first_name", ""),
                last_name=user_dict.get("last_name"),
                username=user_dict.get("username"),
                language_code=user_dict.get("language_code"),
                is_premium=user_dict.get("is_premium", False),
            )
        except Exception:
            return None


auth_service = AuthService()
