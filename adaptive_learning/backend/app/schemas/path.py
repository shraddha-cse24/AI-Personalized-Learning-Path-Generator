"""Pydantic schemas for learning path, mastery, and next exercises."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExerciseItem(BaseModel):
    """Exercise recommendation item."""

    ucid: str
    label: Optional[str] = None
    name_zh: Optional[str] = None
    difficulty: str
    predicted_p_correct: float
    exercise_base_rate: float
    seen_before: bool = False

    model_config = ConfigDict(extra="allow")


class NextExerciseItem(ExerciseItem):
    """Exercise returned by next-exercises endpoint."""

    concept_code: int
    topic: str
    action: str
    stage: Optional[str] = None
    reason: str

    model_config = ConfigDict(extra="allow")


class PathStepItem(BaseModel):
    """Step in a generated learning path."""

    rank: int
    concept_code: int
    name: str
    title_zh: Optional[str] = None
    area_code: Optional[int] = None
    area_name: Optional[str] = None
    group_code: Optional[int] = None
    concept_label: Optional[str] = None
    stage: str
    level: int
    action: str
    status: str
    mastery: Optional[float] = None
    attempts: int
    accuracy: Optional[float] = None
    priority_score: float
    reason: str
    exercises: List[ExerciseItem] = []
    fallback_used: bool = False
    model_bkt_mastery: Optional[float] = None

    model_config = ConfigDict(extra="allow")


class PathResponse(BaseModel):
    """Response returned by GET /api/students/me/path."""

    student_id: str
    answered: int
    cold_start: bool
    graph_source: str
    locked_topics: int
    notes: List[str] = []
    steps: List[PathStepItem]

    model_config = ConfigDict(extra="allow")


class TopicMasteryItem(BaseModel):
    """Topic mastery status item in student progress."""

    concept_code: int
    name: str
    title_zh: Optional[str] = None
    area_code: Optional[int] = None
    area_name: Optional[str] = None
    group_code: Optional[int] = None
    stage: str
    level: int
    unlocked: bool
    unlock_detail: str
    n_exercises: int
    attempts: int
    correct: int
    accuracy: Optional[float] = None
    mastery: Optional[float] = None
    prior_mastery: float
    status: str
    stalled: bool

    model_config = ConfigDict(extra="allow")


class StatusCounts(BaseModel):
    """Counts of topics by status."""

    new: int = 0
    learning: int = 0
    weak: int = 0
    proficient: int = 0
    mastered: int = 0

    model_config = ConfigDict(extra="allow")


class MasteryResponse(BaseModel):
    """Response returned by GET /api/students/me/mastery."""

    student_id: str
    answered: int
    accuracy: Optional[float] = None
    status_counts: StatusCounts
    graph_source: str
    topics: List[TopicMasteryItem]

    model_config = ConfigDict(extra="allow")
