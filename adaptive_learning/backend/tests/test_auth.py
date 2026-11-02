"""Tests for authentication endpoints, Argon2 hashing, JWT tokens, and get_current_student."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure adaptive_learning directory is in sys.path
ADAPTIVE_LEARNING_DIR = Path(__file__).resolve().parents[2]
if str(ADAPTIVE_LEARNING_DIR) not in sys.path:
    sys.path.insert(0, str(ADAPTIVE_LEARNING_DIR))

from backend.app.config import settings  # noqa: E402
from backend.app.core.security import create_access_token  # noqa: E402
from backend.app.db.base import Base  # noqa: E402
from backend.app.db.session import get_db  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models import Student  # noqa: E402


@pytest.fixture
def auth_test_setup():
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


def test_successful_registration(auth_test_setup):
    """Test successful student registration, Argon2 hashing, and profile creation."""
    client, session_factory = auth_test_setup

    payload = {
        "name": "Jane Doe",
        "email": "Jane.Doe@Example.COM",
        "password": "strongPassword123",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert len(data["id"]) > 0
    assert data["name"] == "Jane Doe"
    # Email normalized to lowercase
    assert data["email"] == "jane.doe@example.com"

    # Verify directly in database that password was hashed with Argon2
    with session_factory() as db:
        student = db.query(Student).filter(Student.email == "jane.doe@example.com").first()
        assert student is not None
        assert student.hashed_password.startswith("$argon2")
        assert student.hashed_password != "strongPassword123"
        # Profile was created
        assert student.profile is not None
        assert student.profile.selected_subject == "junyi-math"


def test_duplicate_email_registration(auth_test_setup):
    """Test that registering an existing email returns HTTP 409 Conflict."""
    client, _ = auth_test_setup

    payload = {
        "name": "Original User",
        "email": "duplicate@example.com",
        "password": "password123",
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    # Attempt to register with the same email in different case
    duplicate_payload = {
        "name": "Second User",
        "email": "DUPLICATE@example.com",
        "password": "differentPassword456",
    }
    res2 = client.post("/api/auth/register", json=duplicate_payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_successful_login(auth_test_setup):
    """Test successful login returning {id, name, email, access_token, token_type}."""
    client, _ = auth_test_setup

    # Register first
    client.post(
        "/api/auth/register",
        json={"name": "Alice Wonderland", "email": "alice@example.com", "password": "alicePassword123"},
    )

    # Login
    login_res = client.post(
        "/api/auth/login",
        json={"email": "Alice@Example.COM", "password": "alicePassword123"},
    )
    assert login_res.status_code == 200

    data = login_res.json()
    assert "id" in data
    assert data["name"] == "Alice Wonderland"
    assert data["email"] == "alice@example.com"
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Validate the JWT token structure
    token = data["access_token"]
    decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert decoded["sub"] == data["id"]
    assert decoded["email"] == "alice@example.com"
    assert "exp" in decoded


def test_login_incorrect_password_and_nonexistent_email(auth_test_setup):
    """Test login failures return HTTP 401."""
    client, _ = auth_test_setup

    client.post(
        "/api/auth/register",
        json={"name": "Bob Builder", "email": "bob@example.com", "password": "correctPassword123"},
    )

    # Wrong password
    res_wrong_pw = client.post(
        "/api/auth/login",
        json={"email": "bob@example.com", "password": "wrongPassword"},
    )
    assert res_wrong_pw.status_code == 401
    assert "Incorrect email or password" in res_wrong_pw.json()["detail"]

    # Non-existent email
    res_unknown_email = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "anyPassword"},
    )
    assert res_unknown_email.status_code == 401
    assert "Incorrect email or password" in res_unknown_email.json()["detail"]


def test_invalid_and_expired_token(auth_test_setup):
    """Test that missing, malformed, or expired tokens reject protected endpoints with HTTP 401."""
    client, _ = auth_test_setup

    # Missing token
    res_no_token = client.get("/api/auth/me")
    assert res_no_token.status_code == 401

    # Malformed token
    res_bad_token = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not.a.valid.jwt.token"},
    )
    assert res_bad_token.status_code == 401

    # Expired token
    expired_token = create_access_token(
        subject="some-student-id",
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )
    res_expired = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res_expired.status_code == 401

    # Token signed with wrong secret key
    forged_token = jwt.encode(
        {"sub": "some-id", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "wrong-unauthorized-secret-key-32-chars-minimum",
        algorithm="HS256",
    )
    res_forged = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert res_forged.status_code == 401


def test_inactive_student(auth_test_setup):
    """Test that deactivated students are rejected at both login and protected endpoints."""
    client, session_factory = auth_test_setup

    # Register student
    reg_res = client.post(
        "/api/auth/register",
        json={"name": "Inactive User", "email": "inactive@example.com", "password": "password123"},
    )
    student_id = reg_res.json()["id"]

    # Generate token before deactivation
    valid_token = create_access_token(subject=student_id)

    # Deactivate student in database
    with session_factory() as db:
        student = db.query(Student).filter(Student.id == student_id).first()
        student.is_active = False
        db.commit()

    # 1. Login attempt must fail with 401
    login_res = client.post(
        "/api/auth/login",
        json={"email": "inactive@example.com", "password": "password123"},
    )
    assert login_res.status_code == 401
    assert "Inactive student account" in login_res.json()["detail"]

    # 2. Protected endpoint with token must fail with 401
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert me_res.status_code == 401
    assert "Inactive student account" in me_res.json()["detail"]


def test_get_current_student_protected_endpoint(auth_test_setup):
    """Test that get_current_student derives student identity from token, returning student info."""
    client, _ = auth_test_setup

    # Register
    client.post(
        "/api/auth/register",
        json={"name": "Charlie Chaplin", "email": "charlie@example.com", "password": "charliePassword1"},
    )

    # Login to get token
    login_res = client.post(
        "/api/auth/login",
        json={"email": "charlie@example.com", "password": "charliePassword1"},
    )
    token = login_res.json()["access_token"]
    student_id = login_res.json()["id"]

    # Access protected route
    me_res = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["id"] == student_id
    assert data["name"] == "Charlie Chaplin"
    assert data["email"] == "charlie@example.com"


def test_auth_route_aliases_without_api_prefix(auth_test_setup):
    """Test frontend compatibility alias routes (/auth/register and /auth/login)."""
    client, _ = auth_test_setup

    # Test /auth/register
    reg_res = client.post(
        "/auth/register",
        json={"name": "Frontend User", "email": "frontend@example.com", "password": "frontendPass123"},
    )
    assert reg_res.status_code == 201

    # Test /auth/login
    login_res = client.post(
        "/auth/login",
        json={"email": "frontend@example.com", "password": "frontendPass123"},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()
