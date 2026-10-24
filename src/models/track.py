from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database.base import Base, utc_now

if TYPE_CHECKING:
    from src.models.user import User
    from src.models.playlist import PlaylistTrack
    from src.models.history import ListeningHistory


class Track(Base):
    """Аудиотрек в медиатеке."""
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Хеш содержимого (SHA-256) для предотвращения дубликатов
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    
    # Метаданные трека
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    artist: Mapped[str] = mapped_column(String(255), index=True, nullable=False, default="Unknown Artist")
    album: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # в секундах
    bit_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # kbps
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # в байтах
    mime_type: Mapped[str] = mapped_column(String(64), default="audio/mpeg", nullable=False)

    # Пути к локальным файлам
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    cover_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Идентификаторы Telegram (для возможного резервного доступа)
    telegram_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    telegram_file_unique_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Загрузивший пользователь и настройки приватности
    uploader_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    uploader: Mapped[Optional["User"]] = relationship("User", back_populates="uploaded_tracks")
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Связи
    user_links: Mapped[List["UserTrack"]] = relationship(
        "UserTrack", back_populates="track", cascade="all, delete-orphan"
    )
    playlist_links: Mapped[List["PlaylistTrack"]] = relationship(
        "PlaylistTrack", back_populates="track", cascade="all, delete-orphan"
    )
    history_records: Mapped[List["ListeningHistory"]] = relationship(
        "ListeningHistory", back_populates="track", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Track id={self.id} title='{self.title}' artist='{self.artist}'>"


class UserTrack(Base):
    """Связь трека с персональной библиотекой пользователя (включая избранное)."""
    __tablename__ = "user_tracks"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    track_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True
    )
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="user_tracks")
    track: Mapped["Track"] = relationship("Track", back_populates="user_links")
