"""Pydantic schemas for student profile and onboarding."""

from datetime import datetime
from typing import Literal, Set
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Supported curriculum subjects and level-to-stage mappings
SUPPORTED_SUBJECTS: Set[str] = {"junyi-math"}
LEVEL_TO_ENGINE_STAGE: dict[str, str] = {
    "beginner": "elementary",
    "intermediate": "junior",
    "advanced": "senior",
}

LearningLevel = Literal["beginner", "intermediate", "advanced"]


class ProfileUpdateRequest(BaseModel):
    """Payload for updating student onboarding preferences."""

    selected_subject: str = Field(
        ...,
        description="Curriculum subject ID, e.g. 'junyi-math'",
    )
    learning_level: LearningLevel = Field(
        ...,
        description="Student self-assessed level: 'beginner', 'intermediate', or 'advanced'",
    )

    @field_validator("selected_subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in SUPPORTED_SUBJECTS:
            raise ValueError(
                f"Subject '{v}' is not supported. Supported subjects: {sorted(SUPPORTED_SUBJECTS)}"
            )
        return cleaned


class ProfileResponse(BaseModel):
    """Student profile response schema."""

    student_id: str
    selected_subject: str
    learning_level: str
    engine_stage: str
    onboarding_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
