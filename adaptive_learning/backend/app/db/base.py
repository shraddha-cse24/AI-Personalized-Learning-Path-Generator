"""SQLAlchemy declarative base and custom database types."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, TypeDecorator
from sqlalchemy.orm import DeclarativeBase


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure a datetime object is timezone-aware in UTC.

    SQLite stores datetimes as strings without offset and may return
    timezone-naive datetime objects. This function guarantees the datetime
    is explicitly associated with timezone.utc.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class UTCDateTime(TypeDecorator):
    """DateTime type that guarantees timezone-aware UTC datetime objects.

    When storing into SQLite/DB, ensures values are UTC datetimes.
    When reading from SQLite/DB, if the value is timezone-naive, attaches timezone.utc.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass
