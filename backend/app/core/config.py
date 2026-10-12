"""Application configuration loaded from environment variables.

All secrets and environment-specific values are read here so that no other
module needs to touch os.environ directly.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """SkillSprint backend settings (.env driven)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "SkillSprint API"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "sqlite:///./skillsprint.db"

    # JWT
    JWT_SECRET_KEY: str = "change-me-to-a-long-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Password hashing cost (tests override to 4; production default is 12)
    BCRYPT_ROUNDS: int = 12

    # CORS (comma-separated list of allowed origins)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # AI
    GEMINI_API_KEY: str = ""

    # Code execution sandbox (production: URL of a sandboxed sidecar service)
    CODE_EXECUTOR_URL: str = ""

    # Rate limiting for AI (Gemini) endpoints: requests per user per minute
    AI_RATE_LIMIT_PER_MINUTE: int = 10

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def gemini_configured(self) -> bool:
        """True when a Gemini API key is present (never exposes the key)."""
        return bool(self.GEMINI_API_KEY.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
