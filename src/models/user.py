from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database.base import Base, utc_now

if TYPE_CHECKING:
    from src.models.track import Track, UserTrack
    from src.models.playlist import Playlist
    from src.models.history import ListeningHistory


class User(Base):
    """Пользователь Telegram."""
    __tablename__ = "users"

    # Telegram user ID (BigInteger для поддержки 64-битных ID)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Связи
    uploaded_tracks: Mapped[List["Track"]] = relationship(
        "Track", back_populates="uploader", cascade="all, delete-orphan"
    )
    user_tracks: Mapped[List["UserTrack"]] = relationship(
        "UserTrack", back_populates="user", cascade="all, delete-orphan"
    )
    playlists: Mapped[List["Playlist"]] = relationship(
        "Playlist", back_populates="user", cascade="all, delete-orphan"
    )
    listening_history: Mapped[List["ListeningHistory"]] = relationship(
        "ListeningHistory", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username='{self.username}'>"
