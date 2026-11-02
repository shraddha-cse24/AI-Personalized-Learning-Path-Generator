"""Authentication router for registration and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_student
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.db.session import get_db
from backend.app.models import Student, StudentProfile
from backend.app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)

router = APIRouter(tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student",
    description="Registers a new student account, initializes profile, and returns student details.",
)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """Register a new student account.

    Normalizes email, checks for duplicates (HTTP 409), hashes password
    with Argon2, creates Student and initial StudentProfile records.
    """
    normalized_email = request.email.strip().lower()

    # Check if an account already exists with this email
    existing_student = db.scalars(
        select(Student).where(Student.email == normalized_email)
    ).first()

    if existing_student is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Hash the password securely using Argon2
    hashed_password = hash_password(request.password)

    # Create Student entity
    student = Student(
        email=normalized_email,
        full_name=request.name.strip(),
        hashed_password=hashed_password,
    )

    # Create default onboarding profile
    profile = StudentProfile(
        student=student,
        selected_subject="junyi-math",
        learning_level="beginner",
        engine_stage="elementary",
        onboarding_completed=False,
    )

    db.add(student)
    db.add(profile)
    db.commit()
    db.refresh(student)

    # Issue JWT token on registration for immediate authenticated onboarding
    access_token = create_access_token(
        subject=student.id,
        extra_claims={"email": student.email},
    )

    return RegisterResponse(
        id=student.id,
        name=student.full_name,
        email=student.email,
        access_token=access_token,
        token_type="bearer",
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in an existing student",
    description="Authenticates student credentials and returns an access token.",
)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Log in an existing student.

    Verifies email and password. Rejects invalid credentials with HTTP 401.
    Issues a signed JWT access token.
    """
    normalized_email = request.email.strip().lower()

    student = db.scalars(
        select(Student).where(Student.email == normalized_email)
    ).first()

    # Reject if student not found or password doesn't match
    if student is None or not verify_password(request.password, student.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reject deactivated accounts
    if not student.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive student account",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue JWT token with student ID as subject
    access_token = create_access_token(
        subject=student.id,
        extra_claims={"email": student.email},
    )

    return LoginResponse(
        id=student.id,
        name=student.full_name,
        email=student.email,
        access_token=access_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=RegisterResponse,
    summary="Get current student profile",
    description="Returns the authenticated student derived from the verified JWT token.",
)
async def get_me(
    current_student: Student = Depends(get_current_student),
) -> RegisterResponse:
    """Return identity of the authenticated student."""
    return RegisterResponse(
        id=current_student.id,
        name=current_student.full_name,
        email=current_student.email,
    )
