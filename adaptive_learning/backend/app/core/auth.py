"""Authentication dependencies for protected FastAPI routes."""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import decode_access_token
from backend.app.db.session import get_db
from backend.app.models.student import Student

# Security scheme expecting 'Authorization: Bearer <token>'
# auto_error=False allows uniform HTTP 401 responses on missing/malformed headers
http_bearer = HTTPBearer(auto_error=False)


async def get_current_student(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: Session = Depends(get_db),
) -> Student:
    """Dependency that authenticates the student via JWT bearer token.

    Derives student identity from the verified token signature.
    Rejects missing, expired, invalid tokens, nonexistent students,
    and inactive accounts with HTTP 401 Unauthorized.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        student_id: Optional[str] = payload.get("sub")
        if not student_id:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    stmt = select(Student).where(Student.id == student_id)
    student = db.scalars(stmt).first()

    if student is None:
        raise credentials_exception

    if not student.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive student account",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return student
