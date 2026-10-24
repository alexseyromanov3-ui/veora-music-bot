from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database.base import Base, utc_now

if TYPE_CHECKING:
    from src.models.user import User
    from src.models.track import Track


class ListeningHistory(Base):
    """История прослушиваний треков пользователями."""
    __tablename__ = "listening_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    track_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    duration_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # в секундах
    listened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="listening_history")
    track: Mapped["Track"] = relationship("Track", back_populates="history_records")

    def __repr__(self) -> str:
        return f"<ListeningHistory user_id={self.user_id} track_id={self.track_id} listened_at={self.listened_at}>"
