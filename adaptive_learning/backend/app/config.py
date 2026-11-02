"""Application configuration settings."""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory anchoring to adaptive_learning root
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH: Path = BASE_DIR / "adaptive_learning.db"


class Settings(BaseSettings):
    """Application settings with environment variable support and safe defaults."""

    # Project metadata
    PROJECT_NAME: str = "AI-Based Personalized Learning Path Recommendation System"
    VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"

    # CORS configuration
    # Allows the local React development server running on Vite / CRA
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Database configuration
    # Fixed project-relative location by default, configurable via DATABASE_URL env var
    DATABASE_URL: str = f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
    DB_ECHO: bool = False

    # Authentication & JWT configuration
    # Overridable via JWT_SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES env vars
    JWT_SECRET_KEY: str = "insecure-dev-secret-key-change-in-production-must-be-at-least-32-chars-long!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore",
    )


# Global settings instance
settings = Settings()
