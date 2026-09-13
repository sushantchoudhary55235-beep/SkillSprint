"""Declarative base, shared column types, and timestamp mixins.

All models inherit from Base so Alembic autogenerate sees the full metadata,
and constraint names stay stable across databases.
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, JSON, MetaData, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# BIGINT primary keys on PostgreSQL; plain INTEGER on SQLite so that
# autoincrement (rowid alias) keeps working in local development.
BIGINT_PK = BigInteger().with_variant(Integer(), "sqlite")

# JSONB on PostgreSQL, plain JSON on SQLite (docs/Database_design_docs.md §32).
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class CreatedAtMixin:
    """Table only records creation time (per docs/Database_design_docs.md)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class TimestampMixin(CreatedAtMixin):
    """Table tracks both creation and last update."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
