"""Auth request/response schemas (docs/API_Specification.md §8)."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StudentRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class TeacherRegisterRequest(StudentRegisterRequest):
    employee_id: str | None = Field(default=None, max_length=50)
    department: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str


class StudentRegisterData(BaseModel):
    student_id: str
    name: str
    email: str
    role: str


class TeacherRegisterData(BaseModel):
    employee_id: str | None
    department: str | None
    name: str
    email: str
    role: str


class LoginData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class CurrentUserData(BaseModel):
    """GET /api/auth/me payload."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    student_id: str | None = None
    employee_id: str | None = None
    department: str | None = None
