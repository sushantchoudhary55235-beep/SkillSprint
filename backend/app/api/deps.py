"""FastAPI dependencies: current-user resolution and RBAC guards.

The backend independently enforces authorization (Phases.md §7) —
frontend route protection is never trusted.
"""
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, ForbiddenError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)] = None,
    db: Session = Depends(get_db),
) -> User:
    """Resolve the User from a Bearer token; 401 for missing/invalid/expired."""
    if credentials is None:
        raise AuthError("Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise AuthError("Invalid or expired token")
    subject = payload.get("sub")
    if subject is None:
        raise AuthError("Invalid token payload")
    user = db.get(User, int(subject))
    if user is None:
        raise AuthError("User no longer exists")
    if not user.is_active:
        raise AuthError("Account is deactivated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed: UserRole):
    """Dependency factory: allow only users whose role is in ``allowed``."""

    def checker(user: CurrentUser) -> User:
        if user.role not in {role.value for role in allowed}:
            raise ForbiddenError("You do not have permission to access this resource")
        return user

    return checker


# Role-guard dependencies used across routes.
require_student = require_roles(UserRole.STUDENT)
require_teacher = require_roles(UserRole.TEACHER)
require_admin = require_roles(UserRole.ADMIN)
