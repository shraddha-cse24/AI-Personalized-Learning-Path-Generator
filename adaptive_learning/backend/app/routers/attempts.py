"""Router for learning exercise attempts."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_student
from backend.app.db.session import get_db
from backend.app.models.attempt import Attempt
from backend.app.models.student import Student
from backend.app.schemas.attempt import (
    AttemptCreateRequest,
    AttemptHistoryItem,
    AttemptHistoryResponse,
    AttemptResponse,
)
from backend.app.services.engine_service import engine_service

router = APIRouter(tags=["Attempts"])


@router.post(
    "",
    response_model=AttemptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a student exercise attempt",
    description="Validates exercise UCID, derives concept code, persists attempt to SQLite, and updates recommendation engine.",
)
@router.post(
    "/",
    response_model=AttemptResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_attempt(
    request: AttemptCreateRequest,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> AttemptResponse:
    """Record an exercise attempt for the authenticated student.

    Enforces student data isolation: students can only submit attempts for themselves.
    """
    # Enforce data isolation: student_id must match current_student if supplied
    if request.student_id is not None and request.student_id != current_student.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: you cannot submit attempts for other students.",
        )

    attempt = engine_service.record_attempt(
        student_id=current_student.id,
        ucid=request.ucid,
        is_correct=request.is_correct,
        db=db,
        timestamp=request.timestamp,
    )

    return AttemptResponse(
        id=attempt.id,
        student_id=attempt.student_id,
        ucid=attempt.ucid,
        concept_code=attempt.concept_code,
        is_correct=attempt.is_correct,
        timestamp=attempt.timestamp,
        ok=True,
    )


@router.get(
    "",
    response_model=AttemptHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current student attempt history",
    description="Returns chronological exercise attempts recorded for the authenticated student.",
)
@router.get(
    "/",
    response_model=AttemptHistoryResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_my_attempts(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> AttemptHistoryResponse:
    """List historical attempts for the authenticated student in chronological order."""
    stmt = (
        select(Attempt)
        .where(Attempt.student_id == current_student.id)
        .order_by(Attempt.timestamp.asc(), Attempt.id.asc())
        .offset(offset)
        .limit(limit)
    )
    attempts = db.scalars(stmt).all()

    total_stmt = select(Attempt).where(Attempt.student_id == current_student.id)
    total_count = len(db.scalars(total_stmt).all())

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
