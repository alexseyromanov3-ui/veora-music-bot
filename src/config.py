from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация проекта Telegram Music Player."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram
    BOT_TOKEN: str = "MOCK_TOKEN"
    WEBAPP_URL: str = "http://localhost:8000/webapp"
    STORAGE_CHANNEL_ID: str = "-1004334143448"
    SAVE_LOCAL_AUDIO: bool = False

    # База данных
    DATABASE_URL: str = "sqlite+aiosqlite:///./musicbot.db"

    # Сервер FastAPI
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True

    # Пути к медиа
    MEDIA_DIR: Path = Path("./media")
    AUDIO_DIR: Path = Path("./media/audio")
    COVERS_DIR: Path = Path("./media/covers")

    # Лимиты и безопасность
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20 МБ
    SECRET_KEY: str = "super_secret_signing_key_for_music_bot_app"
    INIT_DATA_TTL_SECONDS: int = 86400  # 24 часа

    def ensure_directories(self) -> None:
        """Создает необходимые директории, если они отсутствуют."""
        self.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        self.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        self.COVERS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
