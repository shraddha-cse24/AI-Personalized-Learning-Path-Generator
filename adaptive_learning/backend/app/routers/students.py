"""Student and profile management router."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_student
from backend.app.db.session import get_db
from backend.app.models import Student, StudentProfile
from backend.app.models.attempt import Attempt
from backend.app.schemas.attempt import AttemptHistoryItem, AttemptHistoryResponse
from backend.app.schemas.path import MasteryResponse, NextExerciseItem, PathResponse
from backend.app.schemas.profile import (
    LEVEL_TO_ENGINE_STAGE,
    ProfileResponse,
    ProfileUpdateRequest,
)
from backend.app.services.engine_service import engine_service

router = APIRouter(tags=["Students & Profile"])


def _assert_student_access(student_id: str, current_student: Student) -> None:
    """Ensure the authenticated student can only access their own data."""
    if student_id != "me" and student_id != current_student.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you can only access your own student data.",
        )


@router.get(
    "/me/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current student profile",
    description="Returns the authenticated student's profile, creating a default one if it does not exist.",
)
async def get_my_profile(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Retrieve the authenticated student's profile."""
    stmt = select(StudentProfile).where(StudentProfile.student_id == current_student.id)
    profile = db.scalars(stmt).first()

    if profile is None:
        profile = StudentProfile(
            student_id=current_student.id,
            selected_subject="junyi-math",
            learning_level="beginner",
            engine_stage="elementary",
            onboarding_completed=False,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return ProfileResponse(
        student_id=profile.student_id,
        selected_subject=profile.selected_subject,
        learning_level=profile.learning_level,
        engine_stage=profile.engine_stage,
        onboarding_completed=profile.onboarding_completed,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get(
    "/{student_id}/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get student profile by ID",
    description="Returns profile for specified student ID after verifying student authorization.",
)
async def get_student_profile(
    student_id: str,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Retrieve profile for the given student ID, enforcing data isolation."""
    _assert_student_access(student_id, current_student)
    return await get_my_profile(current_student=current_student, db=db)


@router.put(
    "/me/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update onboarding preferences",
    description="Updates the authenticated student's subject, level, and mapped engine stage.",
)
async def update_my_profile(
    request: ProfileUpdateRequest,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Update onboarding preferences for the authenticated student.

    Maps learning_level to engine_stage:
      - beginner     -> elementary
      - intermediate -> junior
      - advanced     -> senior
    Marks onboarding_completed as True and syncs placement to recommendation engine.
    """
    mapped_stage = LEVEL_TO_ENGINE_STAGE[request.learning_level]

    stmt = select(StudentProfile).where(StudentProfile.student_id == current_student.id)
    profile = db.scalars(stmt).first()

    if profile is None:
        profile = StudentProfile(
            student_id=current_student.id,
            selected_subject=request.selected_subject,
            learning_level=request.learning_level,
            engine_stage=mapped_stage,
            onboarding_completed=True,
        )
        db.add(profile)
    else:
        profile.selected_subject = request.selected_subject
        profile.learning_level = request.learning_level
        profile.engine_stage = mapped_stage
        profile.onboarding_completed = True

    db.commit()
    db.refresh(profile)

    # Sync stage placement into the recommendation engine
    engine_service.update_student_stage(current_student.id, mapped_stage)

    return ProfileResponse(
        student_id=profile.student_id,
        selected_subject=profile.selected_subject,
        learning_level=profile.learning_level,
        engine_stage=profile.engine_stage,
        onboarding_completed=profile.onboarding_completed,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


# -----------------------------------------------------------------------------
# Learning Path Endpoints
# -----------------------------------------------------------------------------


@router.get(
    "/me/path",
    response_model=PathResponse,
    status_code=status.HTTP_200_OK,
    summary="Get personalized learning path",
    description="Returns an ordered learning path of curriculum topic steps with ranked exercises.",
)
async def get_my_learning_path(
    n_steps: int = Query(5, ge=1, le=20, description="Number of curriculum steps in path"),
    exercises_per_step: int = Query(3, ge=1, le=10, description="Exercises to rank per step"),
    exercise_steps: int = Query(1, ge=1, le=5, description="Steps for which to generate exercises"),
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> PathResponse:
    """Generate personalized learning path for the authenticated student."""
    path_data = engine_service.get_learning_path(
        student_id=current_student.id,
        db=db,
        n_steps=n_steps,
        exercises_per_step=exercises_per_step,
        exercise_steps=exercise_steps,
    )
    return PathResponse(**path_data)


@router.get(
    "/{student_id}/path",
    response_model=PathResponse,
    status_code=status.HTTP_200_OK,
    summary="Get personalized learning path for student ID",
)
async def get_student_learning_path(
    student_id: str,
    n_steps: int = Query(5, ge=1, le=20),
    exercises_per_step: int = Query(3, ge=1, le=10),
    exercise_steps: int = Query(1, ge=1, le=5),
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> PathResponse:
    """Generate learning path enforcing student data isolation."""
    _assert_student_access(student_id, current_student)
    return await get_my_learning_path(
        n_steps=n_steps,
        exercises_per_step=exercises_per_step,
        exercise_steps=exercise_steps,
        current_student=current_student,
        db=db,
    )


# -----------------------------------------------------------------------------
# Mastery & Progress Endpoints
# -----------------------------------------------------------------------------


@router.get(
    "/me/mastery",
    response_model=MasteryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get curriculum mastery summary",
    description="Returns status, smoothed accuracy, and mastery metrics across all curriculum topics.",
)
async def get_my_mastery(
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> MasteryResponse:
    """Return curriculum mastery and topic status for the authenticated student."""
    mastery_data = engine_service.get_mastery(student_id=current_student.id, db=db)
    return MasteryResponse(**mastery_data)


@router.get(
    "/{student_id}/mastery",
    response_model=MasteryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get curriculum mastery summary for student ID",
)
async def get_student_mastery(
    student_id: str,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> MasteryResponse:
    """Return mastery metrics enforcing student data isolation."""
    _assert_student_access(student_id, current_student)
    return await get_my_mastery(current_student=current_student, db=db)


# -----------------------------------------------------------------------------
# Next Exercises Endpoints
# -----------------------------------------------------------------------------


@router.get(
    "/me/next-exercises",
    response_model=List[NextExerciseItem],
    status_code=status.HTTP_200_OK,
    summary="Get next recommended practice exercises",
    description="Returns next exercises from the top topic in the student's learning path or a specific topic.",
)
async def get_my_next_exercises(
    k: int = Query(3, ge=1, le=10, description="Number of candidate exercises to return"),
    concept_code: Optional[int] = Query(None, description="Optional concept code to fetch exercises for a specific topic"),
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> List[NextExerciseItem]:
    """Return next recommended exercises for the authenticated student."""
    exercises = engine_service.get_next_exercises(
        student_id=current_student.id, db=db, k=k, concept_code=concept_code
    )
    return [NextExerciseItem(**ex) for ex in exercises]


@router.get(
    "/{student_id}/next-exercises",
    response_model=List[NextExerciseItem],
    status_code=status.HTTP_200_OK,
    summary="Get next recommended practice exercises for student ID",
)
async def get_student_next_exercises(
    student_id: str,
    k: int = Query(3, ge=1, le=10),
    concept_code: Optional[int] = Query(None),
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> List[NextExerciseItem]:
    """Return next recommended exercises enforcing student data isolation."""
    _assert_student_access(student_id, current_student)
    return await get_my_next_exercises(k=k, concept_code=concept_code, current_student=current_student, db=db)


# -----------------------------------------------------------------------------
# Student Attempts History Endpoints
# -----------------------------------------------------------------------------


@router.get(
    "/me/attempts",
    response_model=AttemptHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get student exercise attempt history",
)
async def get_my_student_attempts(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> AttemptHistoryResponse:
    """Return attempt history for the authenticated student."""
    stmt = (
        select(Attempt)
        .where(Attempt.student_id == current_student.id)
        .order_by(Attempt.timestamp.asc(), Attempt.id.asc())
        .offset(offset)
        .limit(limit)
    )
    attempts = db.scalars(stmt).all()
    total_count = len(db.scalars(select(Attempt).where(Attempt.student_id == current_student.id)).all())

    return AttemptHistoryResponse(
        student_id=current_student.id,
        total=total_count,
        attempts=[
            AttemptHistoryItem(
                id=a.id,
                student_id=a.student_id,
                ucid=a.ucid,
                concept_code=a.concept_code,
                is_correct=a.is_correct,
                timestamp=a.timestamp,
            )
            for a in attempts
        ],
    )


@router.get(
    "/{student_id}/attempts",
    response_model=AttemptHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get student exercise attempt history for student ID",
)
async def get_student_attempts(
    student_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> AttemptHistoryResponse:
    """Return attempt history enforcing student data isolation."""
    _assert_student_access(student_id, current_student)
    return await get_my_student_attempts(limit=limit, offset=offset, current_student=current_student, db=db)
