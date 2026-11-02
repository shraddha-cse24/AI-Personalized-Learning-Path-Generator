"""Tests for database models, relationships, constraints, and chronological ordering."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure adaptive_learning directory is in sys.path
ADAPTIVE_LEARNING_DIR = Path(__file__).resolve().parents[2]
if str(ADAPTIVE_LEARNING_DIR) not in sys.path:
    sys.path.insert(0, str(ADAPTIVE_LEARNING_DIR))

from backend.app.db.base import Base, ensure_utc  # noqa: E402
from backend.app.models import Attempt, Student, StudentProfile  # noqa: E402


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database for testing with foreign keys enabled."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign keys for SQLite
    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


def test_successful_student_creation(db_session):
    """Test creating and retrieving a Student record with default active status and UTC timestamps."""
    student = Student(
        email="learner@example.com",
        full_name="Alice Smith",
        hashed_password="hashed_pw_secret_123",
    )
    db_session.add(student)
    db_session.commit()

    # Query using SQLAlchemy 2.x select
    stmt = select(Student).where(Student.email == "learner@example.com")
    retrieved = db_session.scalars(stmt).one()

    assert retrieved.id is not None
    assert len(retrieved.id) > 0
    assert retrieved.email == "learner@example.com"
    assert retrieved.full_name == "Alice Smith"
    assert retrieved.hashed_password == "hashed_pw_secret_123"
    assert retrieved.is_active is True
    assert retrieved.created_at is not None
    assert retrieved.created_at.tzinfo == timezone.utc
    assert retrieved.updated_at is not None
    assert retrieved.updated_at.tzinfo == timezone.utc


def test_student_profile_relationship_and_deactivation(db_session):
    """Test 1-to-1 relationship between Student and StudentProfile and account deactivation."""
    student = Student(
        email="bob@example.com",
        full_name="Bob Jones",
        hashed_password="hashed_pw_secret_456",
    )
    profile = StudentProfile(
        selected_subject="junyi-math",
        learning_level="intermediate",
        engine_stage="junior",
        onboarding_completed=True,
    )
    student.profile = profile
    db_session.add(student)
    db_session.commit()

    # Verify bidirectional navigation
    stmt = select(Student).where(Student.email == "bob@example.com")
    retrieved_student = db_session.scalars(stmt).one()
    assert retrieved_student.profile is not None
    assert retrieved_student.profile.learning_level == "intermediate"
    assert retrieved_student.profile.engine_stage == "junior"
    assert retrieved_student.profile.student_id == retrieved_student.id

    # Verify student account deactivation preserves records instead of deletion
    retrieved_student.is_active = False
    db_session.commit()

    check_student = db_session.scalars(stmt).one()
    assert check_student.is_active is False
    assert check_student.profile is not None


def test_attempt_creation_and_retrieval(db_session):
    """Test creating and retrieving an attempt linked to a student."""
    student = Student(
        email="charlie@example.com",
        full_name="Charlie Brown",
        hashed_password="hashed_pw_secret_789",
    )
    db_session.add(student)
    db_session.commit()

    attempt = Attempt(
        student_id=student.id,
        ucid="KDOmuTrY/IJzDP4kIgIYCBiGyTymsJ8Iy4cDB35WGYg=",
        concept_code=0,
        is_correct=True,
    )
    db_session.add(attempt)
    db_session.commit()

    stmt = select(Attempt).where(Attempt.student_id == student.id)
    retrieved_attempt = db_session.scalars(stmt).one()

    assert retrieved_attempt.id is not None
    assert retrieved_attempt.ucid == "KDOmuTrY/IJzDP4kIgIYCBiGyTymsJ8Iy4cDB35WGYg="
    assert retrieved_attempt.concept_code == 0
    assert retrieved_attempt.is_correct is True
    assert retrieved_attempt.timestamp is not None
    assert retrieved_attempt.timestamp.tzinfo == timezone.utc
    assert retrieved_attempt.student.email == "charlie@example.com"


def test_foreign_key_enforcement(db_session):
    """Test that SQLite PRAGMA foreign_keys=ON rejects attempts and profiles for nonexistent students."""
    # Attempt to insert profile with non-existent student_id
    invalid_profile = StudentProfile(
        student_id="nonexistent-student-id-123",
        selected_subject="junyi-math",
    )
    db_session.add(invalid_profile)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Attempt to insert attempt with non-existent student_id
    invalid_attempt = Attempt(
        student_id="nonexistent-student-id-123",
        ucid="some_ucid",
        concept_code=1,
        is_correct=False,
    )
    db_session.add(invalid_attempt)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unique_email_constraint(db_session):
    """Test that duplicate emails are rejected by unique constraint."""
    student1 = Student(
        email="duplicate@example.com",
        full_name="First Student",
        hashed_password="hash1",
    )
    db_session.add(student1)
    db_session.commit()

    student2 = Student(
        email="duplicate@example.com",
        full_name="Second Student",
        hashed_password="hash2",
    )
    db_session.add(student2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_chronological_attempt_retrieval(db_session):
    """Test that attempts are reliably retrieved in chronological order for engine reconstruction."""
    student = Student(
        email="replay@example.com",
        full_name="Replay Learner",
        hashed_password="hash_replay",
    )
    db_session.add(student)
    db_session.commit()

    base_time = datetime.now(timezone.utc)
    t1 = base_time - timedelta(days=3)
    t2 = base_time - timedelta(days=2)
    t3 = base_time - timedelta(days=1)
    t4 = base_time

    # Insert out of chronological order to verify that query sorting is authoritative
    attempts_to_insert = [
        Attempt(student_id=student.id, ucid="ex_3", concept_code=2, is_correct=True, timestamp=t3),
        Attempt(student_id=student.id, ucid="ex_1", concept_code=0, is_correct=False, timestamp=t1),
        Attempt(student_id=student.id, ucid="ex_4", concept_code=3, is_correct=True, timestamp=t4),
        Attempt(student_id=student.id, ucid="ex_2", concept_code=1, is_correct=True, timestamp=t2),
    ]
    db_session.add_all(attempts_to_insert)
    db_session.commit()

    # Retrieve ordered by timestamp ASC, id ASC (matching ix_attempts_replay index)
    stmt = (
        select(Attempt)
        .where(Attempt.student_id == student.id)
        .order_by(Attempt.timestamp.asc(), Attempt.id.asc())
    )
    results = db_session.scalars(stmt).all()

    # Verify chronological sequence
    assert len(results) == 4
    assert [a.ucid for a in results] == ["ex_1", "ex_2", "ex_3", "ex_4"]
    assert [a.is_correct for a in results] == [False, True, True, True]

    # Format into (ts, ucid, is_correct) expected by Member 3's engine.load_history
    history_tuples = [(ensure_utc(a.timestamp), a.ucid, a.is_correct) for a in results]
    assert len(history_tuples) == 4
    assert history_tuples[0] == (t1, "ex_1", False)
    assert history_tuples[1] == (t2, "ex_2", True)
    assert history_tuples[2] == (t3, "ex_3", True)
    assert history_tuples[3] == (t4, "ex_4", True)


def test_timestamp_utc_normalization(db_session):
    """Test that timestamps are consistently normalized to UTC regardless of SQLite dialect quirks."""
    student = Student(
        email="utc_check@example.com",
        full_name="UTC Checker",
        hashed_password="pw_hash_utc",
    )
    db_session.add(student)
    db_session.commit()

    # Test with explicitly timezone-naive timestamp written to SQLite
    now_naive = datetime(2026, 11, 1, 12, 0, 0)  # naive
    attempt = Attempt(
        student_id=student.id,
        ucid="ex_naive_test",
        concept_code=5,
        is_correct=True,
        timestamp=now_naive,
    )
    db_session.add(attempt)
    db_session.commit()

    # Expire session cache to force reloading raw data from SQLite
    db_session.expire_all()

    stmt = select(Attempt).where(Attempt.ucid == "ex_naive_test")
    retrieved = db_session.scalars(stmt).one()

    # 1. Column-level UTCDateTime ensures tzinfo is UTC upon loading from SQLite
    assert retrieved.timestamp.tzinfo == timezone.utc

    # 2. ensure_utc helper safely normalizes any datetime
    normalized = ensure_utc(retrieved.timestamp)
    assert normalized.tzinfo == timezone.utc
    assert normalized.hour == 12

    # Helper handles None safely
    assert ensure_utc(None) is None

    # Helper handles arbitrary raw naive datetime
    arbitrary_naive = datetime(2026, 1, 1, 10, 0, 0)
    assert arbitrary_naive.tzinfo is None
    arbitrary_normalized = ensure_utc(arbitrary_naive)
    assert arbitrary_normalized.tzinfo == timezone.utc
    assert arbitrary_normalized.year == 2026
    assert arbitrary_normalized.hour == 10
