"""Comprehensive backend integration tests.

Verifies:
- RecommendationEngine & LearningPredictor initialization with real artifacts.
- Student onboarding & engine stage mapping.
- Attempt recording (POST /api/attempts), UCID validation, and state persistence.
- Learning path generation (GET /api/students/me/path).
- Curriculum mastery (GET /api/students/me/mastery).
- Next exercises (GET /api/students/me/next-exercises).
- Strict student data isolation (HTTP 403 for unauthorized access).
- Safe timestamp handling and duplicate history replay avoidance.
- Concurrency safety under multithreaded requests.
"""

from __future__ import annotations

import concurrent.futures
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ADAPTIVE_LEARNING_DIR = Path(__file__).resolve().parents[2]
if str(ADAPTIVE_LEARNING_DIR) not in sys.path:
    sys.path.insert(0, str(ADAPTIVE_LEARNING_DIR))

from backend.app.db.base import Base  # noqa: E402
from backend.app.db.session import get_db  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models import Attempt, Student, StudentProfile  # noqa: E402
from backend.app.services.engine_service import engine_service, get_engine  # noqa: E402


@pytest.fixture
def integration_client():
    """Create isolated in-memory test database, reset engine student state, and return TestClient."""
    test_db_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_db_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_db_engine)
    TestingSessionLocal = sessionmaker(
        bind=test_db_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    db_lock = threading.Lock()

    def override_get_db():
        with db_lock:
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

    app.dependency_overrides[get_db] = override_get_db
    engine_service.reset_all_students()

    client = TestClient(app)
    yield client, TestingSessionLocal

    app.dependency_overrides.clear()
    engine_service.reset_all_students()
    Base.metadata.drop_all(bind=test_db_engine)


def _register_and_get_auth(client: TestClient, name: str, email: str, password: str = "securepass123"):
    """Register student and return auth headers dict with Bearer token."""
    res = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    student_id = data["id"]
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return student_id, headers


# -----------------------------------------------------------------------------
# 1. Engine Initialization Tests
# -----------------------------------------------------------------------------


def test_engine_initializes_with_real_artifacts():
    """Verify that RecommendationEngine initializes with real TopicGraph and predictor."""
    engine = get_engine()
    assert engine is not None
    assert len(engine.graph.concepts) == 171
    assert len(engine.graph.exercises) == 1330
    assert engine.predictor is not None


# -----------------------------------------------------------------------------
# 2. Student Onboarding & Stage Placement Tests
# -----------------------------------------------------------------------------


def test_student_onboarding_and_stage_placement(integration_client):
    """Verify profile update updates engine placement."""
    client, _ = integration_client
    student_id, headers = _register_and_get_auth(client, "Learner One", "learner1@example.com")

    # Initial profile is elementary/beginner
    prof_res = client.get("/api/students/me/profile", headers=headers)
    assert prof_res.status_code == 200
    assert prof_res.json()["learning_level"] == "beginner"
    assert prof_res.json()["engine_stage"] == "elementary"

    # Update to intermediate -> junior stage
    update_res = client.put(
        "/api/students/me/profile",
        headers=headers,
        json={"selected_subject": "junyi-math", "learning_level": "intermediate"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["learning_level"] == "intermediate"
    assert update_res.json()["engine_stage"] == "junior"

    # Get path and verify stage placement begins at junior level
    path_res = client.get("/api/students/me/path", headers=headers)
    assert path_res.status_code == 200
    path_data = path_res.json()
    assert path_data["student_id"] == student_id
    assert len(path_data["steps"]) > 0


# -----------------------------------------------------------------------------
# 3. Attempt Recording Tests (POST /api/attempts)
# -----------------------------------------------------------------------------


def test_post_attempt_valid_exercise(integration_client):
    """Verify valid exercise attempt persists to SQLite and updates engine state."""
    client, session_factory = integration_client
    student_id, headers = _register_and_get_auth(client, "Learner Two", "learner2@example.com")

    # Pick a known real exercise from the engine
    engine = get_engine()
    real_ucid = list(engine.graph.exercises.keys())[0]
    expected_concept = engine.graph.concept_of(real_ucid)

    # Submit correct attempt
    res = client.post(
        "/api/attempts",
        headers=headers,
        json={"ucid": real_ucid, "is_correct": True},
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["student_id"] == student_id
    assert data["ucid"] == real_ucid
    assert data["concept_code"] == expected_concept
    assert data["is_correct"] is True
    assert "timestamp" in data

    # Verify attempt is in SQLite
    with session_factory() as db:
        saved = db.scalars(select(Attempt).where(Attempt.student_id == student_id)).all()
        assert len(saved) == 1
        assert saved[0].ucid == real_ucid
        assert saved[0].concept_code == expected_concept
        assert saved[0].is_correct is True

    # Verify in-memory engine state updated
    learner = engine._learner(student_id)
    assert learner.answered == 1
    assert learner.correct == 1
    assert learner.concept[expected_concept][0] == 1
    assert learner.concept[expected_concept][1] == 1


def test_post_attempt_unknown_ucid_returns_404(integration_client):
    """Verify unknown exercise UCID is rejected with HTTP 404."""
    client, _ = integration_client
    _, headers = _register_and_get_auth(client, "Learner Three", "learner3@example.com")

    res = client.post(
        "/api/attempts",
        headers=headers,
        json={"ucid": "fake_nonexistent_ucid_12345", "is_correct": True},
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_post_attempt_for_another_student_forbidden(integration_client):
    """Verify a student cannot submit attempts for another student."""
    client, _ = integration_client
    student_a_id, headers_a = _register_and_get_auth(client, "Student A", "studentA@example.com")
    student_b_id, headers_b = _register_and_get_auth(client, "Student B", "studentB@example.com")

    engine = get_engine()
    real_ucid = list(engine.graph.exercises.keys())[0]

    # Student A tries to submit attempt with student_b_id
    res = client.post(
        "/api/attempts",
        headers=headers_a,
        json={"student_id": student_b_id, "ucid": real_ucid, "is_correct": True},
    )
    assert res.status_code == 403
    assert "forbidden" in res.json()["detail"].lower()


# -----------------------------------------------------------------------------
# 4. Learning Path Endpoints (GET /api/students/me/path)
# -----------------------------------------------------------------------------


def test_get_learning_path_cold_start(integration_client):
    """Verify cold start path serves foundation topics with clear pedagogy reasons."""
    client, _ = integration_client
    student_id, headers = _register_and_get_auth(client, "Cold Start Learner", "coldstart@example.com")

    res = client.get("/api/students/me/path?n_steps=5", headers=headers)
    assert res.status_code == 200, res.text
    path = res.json()
    assert path["student_id"] == student_id
    assert path["cold_start"] is True
    assert len(path["steps"]) == 5
    for step in path["steps"]:
        assert step["level"] == 0
        assert step["action"] == "advance"
        assert len(step["reason"]) > 10

    # Top step has exercises
    assert len(path["steps"][0]["exercises"]) == 3
    for ex in path["steps"][0]["exercises"]:
        assert ex["ucid"] in get_engine().graph.exercises


def test_adaptation_revises_weak_topic(integration_client):
    """Verify student failure causes the path to adapt and prioritize revision."""
    client, _ = integration_client
    _, headers = _register_and_get_auth(client, "Adaptive Learner", "adaptive@example.com")

    # Get cold start path to find the first topic
    init_path = client.get("/api/students/me/path", headers=headers).json()
    top_step = init_path["steps"][0]
    concept_code = top_step["concept_code"]
    ucids = get_engine().graph.concepts[concept_code].ucids

    # Submit 4 incorrect attempts on this topic
    for i in range(4):
        ucid = ucids[i % len(ucids)]
        res = client.post("/api/attempts", headers=headers, json={"ucid": ucid, "is_correct": False})
        assert res.status_code == 201

    # Check updated path: should now prioritize revise
    updated_path = client.get("/api/students/me/path", headers=headers).json()
    new_top = updated_path["steps"][0]
    assert new_top["concept_code"] == concept_code
    assert new_top["action"] == "revise"
    assert new_top["status"] == "weak"
    assert "below" in new_top["reason"].lower() or "accuracy" in new_top["reason"].lower()


# -----------------------------------------------------------------------------
# 5. Mastery and Next-Exercises Endpoints
# -----------------------------------------------------------------------------


def test_get_mastery_endpoint(integration_client):
    """Verify progress and mastery tracking across curriculum topics."""
    client, _ = integration_client
    student_id, headers = _register_and_get_auth(client, "Mastery Learner", "mastery@example.com")

    res = client.get("/api/students/me/mastery", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["student_id"] == student_id
    assert data["answered"] == 0
    assert len(data["topics"]) == 171
    assert "status_counts" in data
    assert data["status_counts"]["new"] == 171


def test_get_next_exercises_endpoint(integration_client):
    """Verify next-exercises returns valid dataset exercises."""
    client, _ = integration_client
    _, headers = _register_and_get_auth(client, "Exercise Learner", "exercise@example.com")

    res = client.get("/api/students/me/next-exercises?k=3", headers=headers)
    assert res.status_code == 200, res.text
    exercises = res.json()
    assert len(exercises) == 3

    engine = get_engine()
    for ex in exercises:
        assert ex["ucid"] in engine.graph.exercises
        assert ex["topic"] is not None
        assert ex["action"] in ("advance", "practice", "revise", "review")
        assert ex["difficulty"] in ("easy", "normal", "hard")


# -----------------------------------------------------------------------------
# 6. Student Data Isolation Tests
# -----------------------------------------------------------------------------


def test_student_data_isolation(integration_client):
    """Verify Student A cannot access Student B's profile, path, mastery, next-exercises, or attempts."""
    client, _ = integration_client
    student_a_id, headers_a = _register_and_get_auth(client, "Student A", "alice@example.com")
    student_b_id, headers_b = _register_and_get_auth(client, "Student B", "bob@example.com")

    # Student A attempting to access Student B's path
    res = client.get(f"/api/students/{student_b_id}/path", headers=headers_a)
    assert res.status_code == 403

    # Student A attempting to access Student B's mastery
    res = client.get(f"/api/students/{student_b_id}/mastery", headers=headers_a)
    assert res.status_code == 403

    # Student A attempting to access Student B's next-exercises
    res = client.get(f"/api/students/{student_b_id}/next-exercises", headers=headers_a)
    assert res.status_code == 403

    # Student A attempting to access Student B's profile
    res = client.get(f"/api/students/{student_b_id}/profile", headers=headers_a)
    assert res.status_code == 403

    # Student A attempting to access Student B's attempts
    res = client.get(f"/api/students/{student_b_id}/attempts", headers=headers_a)
    assert res.status_code == 403


def test_unauthenticated_requests_rejected(integration_client):
    """Verify unauthenticated requests to protected endpoints return HTTP 401."""
    client, _ = integration_client

    assert client.get("/api/students/me/profile").status_code == 401
    assert client.get("/api/students/me/path").status_code == 401
    assert client.get("/api/students/me/mastery").status_code == 401
    assert client.get("/api/students/me/next-exercises").status_code == 401
    assert client.post("/api/attempts", json={"ucid": "abc", "is_correct": True}).status_code == 401


# -----------------------------------------------------------------------------
# 7. Safe History Restoration & Duplicate Replay Avoidance
# -----------------------------------------------------------------------------


def test_duplicate_history_replay_avoidance(integration_client):
    """Verify engine doesn't double-count attempts when multiple requests are made."""
    client, _ = integration_client
    student_id, headers = _register_and_get_auth(client, "History Learner", "history@example.com")

    engine = get_engine()
    ucid = list(engine.graph.exercises.keys())[0]

    # Post 1 attempt
    client.post("/api/attempts", headers=headers, json={"ucid": ucid, "is_correct": True})

    # Call get_path multiple times
    client.get("/api/students/me/path", headers=headers)
    client.get("/api/students/me/mastery", headers=headers)
    client.get("/api/students/me/next-exercises", headers=headers)

    # In-memory answered count must still be exactly 1
    learner = engine._learner(student_id)
    assert learner.answered == 1
    assert learner.correct == 1


def test_state_restoration_from_database(integration_client):
    """Verify clearing memory and re-querying accurately restores state from SQLite."""
    client, session_factory = integration_client
    student_id, headers = _register_and_get_auth(client, "Restore Learner", "restore@example.com")

    engine = get_engine()
    ucids = list(engine.graph.exercises.keys())[:3]

    for u in ucids:
        client.post("/api/attempts", headers=headers, json={"ucid": u, "is_correct": True})

    learner_before = engine._learner(student_id)
    assert learner_before.answered == 3

    # Reset engine memory (simulating server reboot)
    engine_service.reset_all_students()

    # Request path -> should restore 3 attempts from SQLite
    res = client.get("/api/students/me/path", headers=headers)
    assert res.status_code == 200
    assert res.json()["answered"] == 3

    learner_after = engine._learner(student_id)
    assert learner_after.answered == 3
    assert learner_after.correct == 3


# -----------------------------------------------------------------------------
# 8. Non-Decreasing Timestamps & Monotonicity
# -----------------------------------------------------------------------------


def test_earlier_timestamp_handled_safely(integration_client):
    """Verify submitting an attempt with an older timestamp doesn't break monotonic invariant."""
    client, _ = integration_client
    student_id, headers = _register_and_get_auth(client, "Time Learner", "time@example.com")

    engine = get_engine()
    ucids = list(engine.graph.exercises.keys())[:2]

    t1 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    t0 = datetime(2026, 1, 15, 11, 0, 0, tzinfo=timezone.utc)  # older

    # First attempt with t1
    res1 = client.post(
        "/api/attempts",
        headers=headers,
        json={"ucid": ucids[0], "is_correct": True, "timestamp": t1.isoformat()},
    )
    assert res1.status_code == 201

    # Second attempt with older t0 should be safely adjusted forward to maintain monotonicity
    res2 = client.post(
        "/api/attempts",
        headers=headers,
        json={"ucid": ucids[1], "is_correct": True, "timestamp": t0.isoformat()},
    )
    assert res2.status_code == 201
    assert res2.json()["student_id"] == student_id


# -----------------------------------------------------------------------------
# 9. Concurrency Safety Test
# -----------------------------------------------------------------------------


def test_concurrent_attempts_recording(integration_client):
    """Verify multithreaded concurrent attempt submissions execute safely without race conditions."""
    client, session_factory = integration_client
    student_id, headers = _register_and_get_auth(client, "Concurrent Learner", "concurrent@example.com")

    engine = get_engine()
    ucids = list(engine.graph.exercises.keys())[:10]

    def submit_one(i):
        return client.post(
            "/api/attempts",
            headers=headers,
            json={"ucid": ucids[i % len(ucids)], "is_correct": i % 2 == 0},
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(submit_one, range(10)))

    for r in results:
        assert r.status_code == 201

    with session_factory() as db:
        attempts = db.scalars(select(Attempt).where(Attempt.student_id == student_id)).all()
        assert len(attempts) == 10

    learner = engine._learner(student_id)
    assert learner.answered == 10


# -----------------------------------------------------------------------------
# 10. Audit & Final Corrections Targeted Tests
# -----------------------------------------------------------------------------


def test_advanced_stage_path_prioritizes_senior_topics(integration_client):
    """Verify selecting Advanced level generates Senior topics first, not Kindergarten counting."""
    client, _ = integration_client
    student_id, headers = _register_and_get_auth(client, "Advanced Learner", "advanced@example.com")

    # Update level to advanced -> senior stage
    up_res = client.put(
        "/api/students/me/profile",
        headers=headers,
        json={"selected_subject": "junyi-math", "learning_level": "advanced"},
    )
    assert up_res.status_code == 200
    assert up_res.json()["engine_stage"] == "senior"

    # Fetch personalized learning path
    path_res = client.get("/api/students/me/path", headers=headers)
    assert path_res.status_code == 200
    steps = path_res.json()["steps"]
    assert len(steps) >= 2

    # First two steps must be senior high school concepts (concepts 124 and 151)
    senior_concepts = {s["concept_code"] for s in steps[:2]}
    assert 124 in senior_concepts or 151 in senior_concepts
    assert steps[0]["stage"] == "senior"
    assert "Senior" in steps[0]["reason"] or "Advanced" in steps[0]["reason"]


def test_intermediate_stage_path_prioritizes_junior_topics(integration_client):
    """Verify selecting Intermediate level generates Junior high school topics first."""
    client, _ = integration_client
    student_id, headers = _register_and_get_auth(client, "Junior Learner", "junior@example.com")

    up_res = client.put(
        "/api/students/me/profile",
        headers=headers,
        json={"selected_subject": "junyi-math", "learning_level": "intermediate"},
    )
    assert up_res.status_code == 200
    assert up_res.json()["engine_stage"] == "junior"

    path_res = client.get("/api/students/me/path", headers=headers)
    assert path_res.status_code == 200
    steps = path_res.json()["steps"]
    assert len(steps) > 0
    assert steps[0]["stage"] == "junior"
    assert "Junior" in steps[0]["reason"] or "Intermediate" in steps[0]["reason"]


def test_next_exercises_for_specific_concept_code(integration_client):
    """Verify passing concept_code returns candidate exercises strictly for that curriculum topic."""
    client, _ = integration_client
    _, headers = _register_and_get_auth(client, "Topic Learner", "topic@example.com")

    # Request exercises specifically for Concept 151 (Exponents: paper folding and powers)
    res = client.get("/api/students/me/next-exercises?concept_code=151&k=2", headers=headers)
    assert res.status_code == 200, res.text
    exercises = res.json()
    assert len(exercises) == 2
    for ex in exercises:
        assert ex["concept_code"] == 151
        assert "Exponents" in ex["topic"]
        assert ex["ucid"] in get_engine().graph.concepts[151].ucids


def test_next_exercises_unknown_concept_returns_404(integration_client):
    """Verify requesting an invalid concept code returns HTTP 404."""
    client, _ = integration_client
    _, headers = _register_and_get_auth(client, "Error Learner", "error@example.com")

    res = client.get("/api/students/me/next-exercises?concept_code=999999", headers=headers)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_mastery_zero_attempts_has_no_artificial_mastery(integration_client):
    """Verify that unattempted curriculum topics have None student mastery and 0% answered accuracy."""
    client, _ = integration_client
    student_id, headers = _register_and_get_auth(client, "Fresh Learner", "fresh@example.com")

    res = client.get("/api/students/me/mastery", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["answered"] == 0
    assert data["accuracy"] is None
    # All topics must have mastery is None until practiced
    for t in data["topics"]:
        assert t["attempts"] == 0
        assert t["mastery"] is None
        assert t["status"] == "new"
