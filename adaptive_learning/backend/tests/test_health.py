"""Tests for the health check endpoint and CORS configuration."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure adaptive_learning directory is in sys.path
ADAPTIVE_LEARNING_DIR = Path(__file__).resolve().parents[2]
if str(ADAPTIVE_LEARNING_DIR) not in sys.path:
    sys.path.insert(0, str(ADAPTIVE_LEARNING_DIR))

from backend.app.main import app  # noqa: E402
from backend.app.config import settings  # noqa: E402


@pytest.fixture
def client():
    """Test client fixture for making API requests."""
    return TestClient(app)


def test_health_check_status_code(client):
    """Test that GET /api/health returns HTTP 200."""
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_check_payload(client):
    """Test that GET /api/health returns the expected JSON response."""
    response = client.get("/api/health")
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == settings.PROJECT_NAME
    assert data["version"] == settings.VERSION


def test_cors_headers_allowed_origin(client):
    """Test that CORS headers are returned for allowed React origins."""
    origin = "http://localhost:5173"
    response = client.get(
        "/api/health",
        headers={"Origin": origin},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin


def test_cors_preflight_request(client):
    """Test CORS OPTIONS preflight request for allowed origins."""
    origin = "http://127.0.0.1:5173"
    headers = {
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type",
    }
    response = client.options("/api/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
