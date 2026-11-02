"""Tests for student profile and onboarding endpoints."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure adaptive_learning directory is in sys.path
ADAPTIVE_LEARNING_DIR = Path(__file__).resolve().parents[2]
if str(ADAPTIVE_LEARNING_DIR) not in sys.path:
    sys.path.insert(0, str(ADAPTIVE_LEARNING_DIR))

from backend.app.db.base import Base  # noqa: E402
from backend.app.db.session import get_db  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models import Student, StudentProfile  # noqa: E402


@pytest.fixture
def profile_test_setup():
    """Create isolated in-memory SQLite database and TestClient with overridden get_db."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable SQLite foreign keys
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

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client, TestingSessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def _register_and_login(client, name="Test User", email="user@example.com", password="password123"):
    """Helper to register and login a user, returning (student_id, access_token)."""
    reg_res = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert reg_res.status_code == 201
    student_id = reg_res.json()["id"]

    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return student_id, token


def test_fetch_existing_profile(profile_test_setup):
    """Test fetching an existing student's profile."""
    client, _ = profile_test_setup
    student_id, token = _register_and_login(client, email="fetcher@example.com")

    response = client.get(
        "/api/students/me/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["student_id"] == student_id
    assert data["selected_subject"] == "junyi-math"
    assert data["learning_level"] == "beginner"
    assert data["engine_stage"] == "elementary"
    assert data["onboarding_completed"] is False
    assert "created_at" in data
    assert "updated_at" in data


def test_create_default_profile_if_missing(profile_test_setup):
    """Test that GET /me/profile creates a default profile if none exists."""
    client, session_factory = profile_test_setup
    student_id, token = _register_and_login(client, email="missing_profile@example.com")

    # Manually delete the student's profile from the database
    with session_factory() as db:
        db.query(StudentProfile).filter(StudentProfile.student_id == student_id).delete()
        db.commit()

    # GET /me/profile should create a default profile on the fly
    response = client.get(
        "/api/students/me/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["student_id"] == student_id
    assert data["selected_subject"] == "junyi-math"
    assert data["learning_level"] == "beginner"
    assert data["engine_stage"] == "elementary"
    assert data["onboarding_completed"] is False

    # Confirm it was persisted in the database
    with session_factory() as db:
        saved_profile = db.query(StudentProfile).filter(StudentProfile.student_id == student_id).first()
        assert saved_profile is not None
        assert saved_profile.selected_subject == "junyi-math"


def test_update_onboarding_details(profile_test_setup):
    """Test updating onboarding preferences and completing onboarding."""
    client, _ = profile_test_setup
    student_id, token = _register_and_login(client, email="updater@example.com")

    update_payload = {
        "selected_subject": "junyi-math",
        "learning_level": "intermediate",
    }
    put_res = client.put(
        "/api/students/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json=update_payload,
    )
    assert put_res.status_code == 200
    data = put_res.json()
    assert data["student_id"] == student_id
    assert data["selected_subject"] == "junyi-math"
    assert data["learning_level"] == "intermediate"
    assert data["engine_stage"] == "junior"
    assert data["onboarding_completed"] is True

    # Verify retrieval reflects updated state
    get_res = client.get(
        "/api/students/me/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["learning_level"] == "intermediate"
    assert get_res.json()["engine_stage"] == "junior"
    assert get_res.json()["onboarding_completed"] is True


def test_level_to_engine_stage_mapping(profile_test_setup):
    """Test all learning_level to engine_stage mappings: beginner->elementary, intermediate->junior, advanced->senior."""
    client, _ = profile_test_setup
    _, token = _register_and_login(client, email="mapper@example.com")

    mappings = [
        ("beginner", "elementary"),
        ("intermediate", "junior"),
        ("advanced", "senior"),
    ]

    for level, expected_stage in mappings:
        res = client.put(
            "/api/students/me/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"selected_subject": "junyi-math", "learning_level": level},
        )
        assert res.status_code == 200
        assert res.json()["learning_level"] == level
        assert res.json()["engine_stage"] == expected_stage


def test_invalid_learning_level_and_subject(profile_test_setup):
    """Test that invalid learning_level or unsupported subject returns HTTP 422 Unprocessable Entity."""
    client, _ = profile_test_setup
    _, token = _register_and_login(client, email="validator@example.com")

    # Invalid learning level
    bad_level_res = client.put(
        "/api/students/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"selected_subject": "junyi-math", "learning_level": "expert"},
    )
    assert bad_level_res.status_code == 422

    # Unsupported subject
    bad_subject_res = client.put(
        "/api/students/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"selected_subject": "physics", "learning_level": "beginner"},
    )
    assert bad_subject_res.status_code == 422


def test_unauthorized_access(profile_test_setup):
    """Test that requests without valid authorization headers return HTTP 401."""
    client, _ = profile_test_setup

    # GET without token
    get_res = client.get("/api/students/me/profile")
    assert get_res.status_code == 401

    # GET with invalid token
    bad_token_res = client.get(
        "/api/students/me/profile",
        headers={"Authorization": "Bearer bad.token.here"},
    )
    assert bad_token_res.status_code == 401

    # PUT without token
    put_res = client.put(
        "/api/students/me/profile",
        json={"selected_subject": "junyi-math", "learning_level": "beginner"},
    )
    assert put_res.status_code == 401


def test_student_isolation_cannot_access_other_profile(profile_test_setup):
    """Test that one student cannot access or modify another student's profile."""
    client, _ = profile_test_setup

    # Register Student A
    id_a, token_a = _register_and_login(client, name="Student A", email="student_a@example.com")
    # Register Student B
    id_b, token_b = _register_and_login(client, name="Student B", email="student_b@example.com")

    # Student A updates to intermediate
    client.put(
        "/api/students/me/profile",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"selected_subject": "junyi-math", "learning_level": "intermediate"},
    )

    # Student B updates to advanced
    client.put(
        "/api/students/me/profile",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"selected_subject": "junyi-math", "learning_level": "advanced"},
    )

    # Student A fetches profile
    res_a = client.get(
        "/api/students/me/profile",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["student_id"] == id_a
    assert data_a["learning_level"] == "intermediate"
    assert data_a["engine_stage"] == "junior"

    # Student B fetches profile
    res_b = client.get(
        "/api/students/me/profile",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["student_id"] == id_b
    assert data_b["learning_level"] == "advanced"
    assert data_b["engine_stage"] == "senior"
