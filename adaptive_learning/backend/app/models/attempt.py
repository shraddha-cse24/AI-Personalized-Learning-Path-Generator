"""Attempt SQLAlchemy ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, UTCDateTime, utc_now

if TYPE_CHECKING:
    from backend.app.models.student import Student


class Attempt(Base):
    """Learning exercise attempt recorded for a student.

    Strictly append-only log of student exercise interactions.
    Never modified or deleted during standard operations.
    """

    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    student_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ucid: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    concept_code: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utc_now,
        nullable=False,
        index=True,
    )

    # Relationships
    student: Mapped["Student"] = relationship(
        "Student",
        back_populates="attempts",
    )

    __table_args__ = (
        # Composite replay index for chronological engine reconstruction
        Index("ix_attempts_replay", "student_id", "timestamp", "id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Attempt id={self.id} student_id={self.student_id!r} "
            f"ucid={self.ucid!r} is_correct={self.is_correct} ts={self.timestamp}>"
        )
