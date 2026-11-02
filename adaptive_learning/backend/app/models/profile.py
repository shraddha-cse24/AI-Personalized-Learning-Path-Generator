"""StudentProfile SQLAlchemy ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, UTCDateTime, utc_now

if TYPE_CHECKING:
    from backend.app.models.student import Student


class StudentProfile(Base):
    """Profile preferences and onboarding state for a student."""

    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    student_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("students.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    selected_subject: Mapped[str] = mapped_column(
        String(50),
        default="junyi-math",
        nullable=False,
    )
    learning_level: Mapped[str] = mapped_column(
        String(20),
        default="beginner",
        nullable=False,
    )
    engine_stage: Mapped[str] = mapped_column(
        String(20),
        default="elementary",
        nullable=False,
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    student: Mapped["Student"] = relationship(
        "Student",
        back_populates="profile",
    )

    def __repr__(self) -> str:
        return f"<StudentProfile id={self.id} student_id={self.student_id!r} stage={self.engine_stage!r}>"
