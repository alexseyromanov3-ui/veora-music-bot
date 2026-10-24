import hashlib
import hmac
import json
import time
import pytest
from pathlib import Path
from src.services.auth import AuthService
from src.services.storage import StorageService


def create_valid_init_data(user_id: int, username: str, bot_token: str) -> str:
    """Генерирует валидную подписанную строку initData для тестов."""
    user_data = {"id": user_id, "first_name": "Test", "username": username}
    auth_date = int(time.time())
    params = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(user_data, separators=(",", ":")),
    }

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    data_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    params["hash"] = data_hash
    return "&".join(f"{k}={v}" for k, v in params.items())


def test_auth_service_valid_init_data() -> None:
    """Проверка успешной верификации корректного initData."""
    token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    init_data = create_valid_init_data(12345, "telegram_user", token)

    user = AuthService.validate_init_data(init_data, bot_token=token)
    assert user is not None
    assert user.id == 12345
    assert user.username == "telegram_user"


def test_auth_service_tampered_init_data() -> None:
    """Проверка отклонения поддельных данных (неверный хеш)."""
    token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    init_data = create_valid_init_data(12345, "telegram_user", token)
    # Подменяем id без пересчета хеша
    tampered_data = init_data.replace("12345", "99999")

    user = AuthService.validate_init_data(tampered_data, bot_token=token)
    assert user is None


def test_auth_service_expired_data() -> None:
    """Проверка отклонения просроченных данных (старше TTL)."""
    token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    # Создаем данные с датой 2 дня назад
    old_time = int(time.time()) - 172800
    user_data = {"id": 1, "first_name": "Old"}
    params = {
        "auth_date": str(old_time),
        "user": json.dumps(user_data, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    expired_init_data = "&".join(f"{k}={v}" for k, v in params.items())

    user = AuthService.validate_init_data(expired_init_data, bot_token=token, ttl_seconds=86400)
    assert user is None


def test_storage_range_header_parsing() -> None:
    """Проверка корректного парсинга HTTP Range заголовков."""
    file_size = 1000

    # bytes=0-499 -> (0, 499)
    assert StorageService.parse_range_header("bytes=0-499", file_size) == (0, 499)

    # bytes=500- -> (500, 999)
    assert StorageService.parse_range_header("bytes=500-", file_size) == (500, 999)

    # bytes=-100 -> последние 100 байт (900, 999)
    assert StorageService.parse_range_header("bytes=-100", file_size) == (900, 999)

    # Некорректные диапазоны
    assert StorageService.parse_range_header("bytes=1500-", file_size) is None
    assert StorageService.parse_range_header("bytes=500-200", file_size) is None
    assert StorageService.parse_range_header("invalid", file_size) is None


def test_format_content_disposition_cyrillic() -> None:
    """Проверка формирования RFC 6266/5987 Content-Disposition для русских названий треков."""
    cyrillic_name = "Король и Шут - Лесник.mp3"
    header = StorageService.format_content_disposition(cyrillic_name, as_attachment=True)
    # Проверяем, что заголовок кодируется в latin-1 без UnicodeEncodeError (требование HTTP/Starlette)
    header_bytes = header.encode("latin-1")
    assert b"attachment" in header_bytes
    assert b"filename*=UTF-8''" in header_bytes
    assert "filename*=UTF-8''%D0%9A%D0%BE%D1%80%D0%BE%D0%BB%D1%8C" in header
