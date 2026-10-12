"""Production configuration guard (audit fix M1).

The startup guard must refuse ENVIRONMENT=production when CORS origins are
missing/wildcard or when the JWT secret is left at its (insecure) default.
Development must never be blocked.
"""
from types import SimpleNamespace

import pytest

from app.main import validate_production_config


def _cfg(**overrides):
    base = dict(
        ENVIRONMENT="production",
        CORS_ORIGINS="https://app.example.com",
        JWT_SECRET_KEY="x" * 40,
    )
    base.update(overrides)
    return SimpleNamespace(
        is_production=base["ENVIRONMENT"].lower() == "production",
        cors_origins=[o.strip() for o in base["CORS_ORIGINS"].split(",") if o.strip()],
        JWT_SECRET_KEY=base["JWT_SECRET_KEY"],
    )


class TestProductionConfigGuard:
    def test_valid_production_config_passes(self):
        validate_production_config(_cfg())  # no exception

    def test_wildcard_cors_rejected(self):
        with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
            validate_production_config(_cfg(CORS_ORIGINS="*"))

    def test_missing_cors_rejected(self):
        with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
            validate_production_config(_cfg(CORS_ORIGINS=""))

    def test_default_jwt_secret_rejected(self):
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
            validate_production_config(_cfg(JWT_SECRET_KEY="change-me-to-a-long-random-secret"))

    def test_empty_jwt_secret_rejected(self):
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
            validate_production_config(_cfg(JWT_SECRET_KEY=""))

    def test_development_is_never_blocked(self):
        dev = _cfg(ENVIRONMENT="development", CORS_ORIGINS="*", JWT_SECRET_KEY="change-me-to-a-long-random-secret")
        validate_production_config(dev)  # no exception
