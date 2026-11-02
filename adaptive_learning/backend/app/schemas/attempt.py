"""Pydantic schemas for learning exercise attempts."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AttemptCreateRequest(BaseModel):
    """Payload for submitting a learning attempt."""

    ucid: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Exercise UCID from the Junyi dataset",
    )
    is_correct: bool = Field(
        ...,
        description="Whether the student solved the exercise correctly",
    )
    student_id: Optional[str] = Field(
        None,
        max_length=36,
        description="Optional student ID; if provided, must match the authenticated student",
    )
    timestamp: Optional[datetime] = Field(
        None,
        description="Optional attempt timestamp (ISO-8601). Defaults to current UTC time.",
    )


class AttemptResponse(BaseModel):
    """Response returned upon successfully recording an attempt."""

    id: int
    student_id: str
    ucid: str
    concept_code: int
    is_correct: bool
    timestamp: datetime
    ok: bool = True

    model_config = ConfigDict(from_attributes=True)


class AttemptHistoryItem(BaseModel):
    """An attempt item in history listing."""

    id: int
    student_id: str
    ucid: str
    concept_code: int
    is_correct: bool
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class AttemptHistoryResponse(BaseModel):
    """Student attempt history listing."""

    student_id: str
    total: int
    attempts: List[AttemptHistoryItem]
