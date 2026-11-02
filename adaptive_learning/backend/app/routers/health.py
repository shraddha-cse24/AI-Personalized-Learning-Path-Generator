"""Health check endpoint router."""

from pydantic import BaseModel
from fastapi import APIRouter

from backend.app.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Schema for health-check response."""

    status: str
    app: str
    version: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the operational status and metadata of the backend service.",
)
async def get_health() -> HealthResponse:
    """Return application health status."""
    return HealthResponse(
        status="healthy",
        app=settings.PROJECT_NAME,
        version=settings.VERSION,
    )
