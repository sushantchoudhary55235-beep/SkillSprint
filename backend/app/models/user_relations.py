"""User <-> profile bidirectional relationships."""
from sqlalchemy.orm import relationship

from app.models.user import User

User.student_profile = relationship(
    "StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
)
User.teacher_profile = relationship(
    "TeacherProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
)
