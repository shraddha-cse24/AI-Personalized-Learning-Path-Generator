"""FastAPI Backend Application Entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.db.base import Base
from backend.app.db.session import engine
from backend.app.routers import attempts, auth, health, students
from backend.app.services.engine_service import get_engine


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Application lifespan events (startup and shutdown)."""
    # Initialize database tables on application startup
    Base.metadata.create_all(bind=engine)
    # Pre-warm TopicGraph, LearningPredictor, and RecommendationEngine
    get_engine()
    yield


def create_app() -> FastAPI:
    """Application factory that initializes and configures the FastAPI application."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure Cross-Origin Resource Sharing (CORS)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routers under the /api prefix
    application.include_router(health.router, prefix=settings.API_PREFIX)
    application.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth")
    application.include_router(students.router, prefix=f"{settings.API_PREFIX}/students")
    application.include_router(attempts.router, prefix=f"{settings.API_PREFIX}/attempts")

    # Additional alias route prefixes for direct frontend compatibility
    application.include_router(auth.router, prefix="/auth", include_in_schema=False)
    application.include_router(students.router, prefix="/students", include_in_schema=False)
    application.include_router(attempts.router, prefix="/attempts", include_in_schema=False)

    return application


# Global application instance for ASGI servers like Uvicorn
app = create_app()
