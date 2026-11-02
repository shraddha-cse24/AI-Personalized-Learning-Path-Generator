"""Student SQLAlchemy ORM model."""

import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, UTCDateTime, utc_now

if TYPE_CHECKING:
    from backend.app.models.profile import StudentProfile
    from backend.app.models.attempt import Attempt


class Student(Base):
    """Student account entity representing registered learners.

    Student learning history is strictly preserved. Account deactivation
    is handled by setting is_active=False without deleting student records.
    """

    __tablename__ = "students"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
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
    profile: Mapped[Optional["StudentProfile"]] = relationship(
        "StudentProfile",
        back_populates="student",
        uselist=False,
        cascade="all, delete-orphan",
    )
    attempts: Mapped[List["Attempt"]] = relationship(
        "Attempt",
        back_populates="student",
        cascade="all, delete-orphan",
        order_by="Attempt.timestamp.asc(), Attempt.id.asc()",
    )

    def __repr__(self) -> str:
        return f"<Student id={self.id!r} email={self.email!r} active={self.is_active}>"
