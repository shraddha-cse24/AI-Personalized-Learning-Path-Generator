"""Routers package for API endpoints."""

from backend.app.routers.attempts import router as attempts_router
from backend.app.routers.auth import router as auth_router
from backend.app.routers.health import router as health_router
from backend.app.routers.students import router as students_router

__all__ = ["health_router", "auth_router", "students_router", "attempts_router"]
