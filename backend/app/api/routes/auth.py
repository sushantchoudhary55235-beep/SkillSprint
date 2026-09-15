"""Authentication endpoints (docs/API_Specification.md §8).

All responses use the standard {success, message, data} envelope via
app.utils.responses.success_response.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.auth import (
    LoginData,
    LoginRequest,
    StudentRegisterData,
    StudentRegisterRequest,
    TeacherRegisterData,
    TeacherRegisterRequest,
)
from app.services.auth import AuthService, current_user_data
from app.utils.responses import success_response

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/register/student", status_code=201)
def register_student(
    req: StudentRegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    profile = service.register_student(req)
    return success_response(
        data=StudentRegisterData(
            student_id=profile.student_id,
            name=profile.user.name,
            email=profile.user.email,
            role=profile.user.role,
        ),
        message="Student registered successfully",
        status_code=201,
    )


@router.post("/register/teacher", status_code=201)
def register_teacher(
    req: TeacherRegisterRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    profile = service.register_teacher(req)
    return success_response(
        data=TeacherRegisterData(
            employee_id=profile.employee_id,
            department=profile.department,
            name=profile.user.name,
            email=profile.user.email,
            role=profile.user.role,
        ),
        message="Teacher registered successfully",
        status_code=201,
    )


@router.post("/login")
def login(req: LoginRequest, service: Annotated[AuthService, Depends(get_auth_service)]):
    data: LoginData = service.login(req)
    return success_response(data=data, message="Login successful")


@router.get("/me")
def me(user: CurrentUser):
    return success_response(data=current_user_data(user), message="Current user retrieved")


@router.post("/logout")
def logout(user: CurrentUser):
    """Stateless JWT logout: the client discards the token.

    The authenticated call proves the token was valid at logout time.
    Token revocation (a server-side denylist) can be added in a later phase
    if session invalidation becomes a requirement.
    """
    return success_response(message="Logged out successfully")
