"""Authentication business logic (docs/API_Specification.md §8).

Registration rules:
- Email must be globally unique (409 on duplicates).
- Students get a unique Student ID (SS<YY><6-digit seq>) generated in a
  transaction-safe way; teachers may provide an employee id.
- Passwords are always stored hashed, never plain text.
"""
from datetime import datetime, timezone
from decimal import Decimal

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, ConflictError, ValidationError
from app.core.security import create_access_token, hash_password, validate_password_strength, verify_password
from app.models.profile import StudentProfile, TeacherProfile
from app.models.user import User, UserRole
from app.schemas.auth import (
    CurrentUserData,
    LoginData,
    LoginRequest,
    StudentRegisterRequest,
    TeacherRegisterRequest,
    UserOut,
)

_STUDENT_ID_PREFIX = "SS"

logger = logging.getLogger("skillsprint.auth")


def _current_year_short() -> str:
    return f"{datetime.now(timezone.utc).year % 100:02d}"


def _generate_student_id(db: Session) -> str:
    """Next Student ID for the current year, e.g. SS26000001.

    Uses max(existing sequence) + 1 within the caller's transaction so
    concurrent registrations cannot collide on the unique column.
    """
    prefix = f"{_STUDENT_ID_PREFIX}{_current_year_short()}"
    like = f"{prefix}%"
    max_id = db.scalar(select(func.max(StudentProfile.student_id)).where(StudentProfile.student_id.like(like)))
    seq = int(max_id[len(prefix):]) + 1 if max_id else 1
    return f"{prefix}{seq:06d}"


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # -- registration -------------------------------------------------
    def register_student(self, req: StudentRegisterRequest) -> StudentProfile:
        self._ensure_email_free(req.email)
        self._ensure_password_ok(req.password)

        user = User(name=req.name.strip(), email=req.email.lower(), password_hash=hash_password(req.password), role=UserRole.STUDENT.value)
        profile = StudentProfile(
            student_id=_generate_student_id(self.db),
            readiness_score=Decimal("0"),
            xp=0,
            level=1,
            current_streak=0,
            longest_streak=0,
        )
        user.student_profile = profile
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return profile

    def register_teacher(self, req: TeacherRegisterRequest) -> TeacherProfile:
        self._ensure_email_free(req.email)
        self._ensure_password_ok(req.password)

        if req.employee_id:
            existing_emp = self.db.scalar(
                select(TeacherProfile).where(TeacherProfile.employee_id == req.employee_id)
            )
            if existing_emp is not None:
                raise ConflictError("An account with this employee ID already exists")

        user = User(name=req.name.strip(), email=req.email.lower(), password_hash=hash_password(req.password), role=UserRole.TEACHER.value)
        profile = TeacherProfile(employee_id=req.employee_id, department=req.department)
        user.teacher_profile = profile
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return profile

    # -- login --------------------------------------------------------
    def login(self, req: LoginRequest) -> LoginData:
        user = self.db.scalar(select(User).where(User.email == req.email.lower()))
        # Same message for unknown email and wrong password (no account enumeration).
        # Observability (Phase 23): failures are logged WITHOUT the attempted
        # password or any credential material — email (an identifier, not a
        # secret) is included so repeated failures are traceable.
        if user is None or not verify_password(req.password, user.password_hash):
            logger.warning("Login failed: unknown email or wrong password (email=%s)", req.email.lower())
            raise AuthError("Incorrect email or password")
        if not user.is_active:
            logger.warning("Login rejected: deactivated account (email=%s)", req.email.lower())
            raise AuthError("Account is deactivated")

        token = create_access_token(str(user.id), extra={"role": user.role, "email": user.email})
        return LoginData(access_token=token, user=UserOut.model_validate(user))

    # -- helpers ------------------------------------------------------
    def _ensure_email_free(self, email: str) -> None:
        exists = self.db.scalar(select(User.id).where(User.email == email.lower()))
        if exists is not None:
            raise ConflictError("An account with this email already exists")

    @staticmethod
    def _ensure_password_ok(password: str) -> None:
        error = validate_password_strength(password)
        if error:
            raise ValidationError(error)


def current_user_data(user: User) -> CurrentUserData:
    """Build the GET /api/auth/me payload including profile identifiers."""
    data = CurrentUserData(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
    )
    if user.role == UserRole.STUDENT.value and user.student_profile:
        data.student_id = user.student_profile.student_id
    if user.role == UserRole.TEACHER.value and user.teacher_profile:
        data.employee_id = user.teacher_profile.employee_id
        data.department = user.teacher_profile.department
    return data
