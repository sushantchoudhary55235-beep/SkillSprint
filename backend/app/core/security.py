"""Security primitives: password hashing and JWT tokens.

Per docs/API_Specification.md §5, requests authenticate with
``Authorization: Bearer <access_token>``.

bcrypt is used directly (passlib is unmaintained and incompatible with
modern bcrypt releases).
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

_MIN_PASSWORD_LENGTH = 8
# bcrypt ignores input beyond 72 bytes; we reject it at validation time so
# login-time comparison matches what was hashed rather than silently truncating.
_MAX_PASSWORD_BYTES = 72

# Cost factor is configurable so tests can drop it (4 is bcrypt's minimum) and
# keep the suite fast; production always uses the default of 12.
BCRYPT_ROUNDS = max(4, min(15, settings.BCRYPT_ROUNDS))


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Malformed hash in DB must not leak a 500 to the client.
        return False


def validate_password_strength(password: str) -> str | None:
    """Return an error message if the password violates policy, else None."""
    if len(password) < _MIN_PASSWORD_LENGTH:
        return f"Password must be at least {_MIN_PASSWORD_LENGTH} characters long"
    if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        return f"Password must be at most {_MAX_PASSWORD_BYTES} bytes"
    return None


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    """Create a signed JWT. ``subject`` is the user id as string; role/email
    ride along as claims for authorization convenience."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT, raising JWTError on tamper/expiry.

    ``exp`` and ``sub`` are mandatory claims: a token without an expiry would
    otherwise be accepted forever, and a token without a subject cannot
    identify a user.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require_exp": True, "require_sub": True},
    )
