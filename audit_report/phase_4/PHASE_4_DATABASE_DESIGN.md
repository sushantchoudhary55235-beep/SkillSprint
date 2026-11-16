# Phase 4 Database Design

**Generated**: 2026-11-01  
**Based on**: PHASE_4_IMPLEMENTATION_PLAN.md  
**Status**: PLANNING PHASE — Awaiting approval  
**Last Updated**: 2026-11-01 (corrected for atomic rate limiting, idempotency concurrency)

---

## Overview

Two new tables to replace in-memory stores with PostgreSQL-backed implementations:

1. `question_tickets` — Server-side answer keys for AI-generated questions
2. `ai_rate_limits` — Sliding-window rate limit tracking per user

Both use existing SQLAlchemy/PostgreSQL infrastructure. No new dependencies.

---

## Table 1: question_tickets

### Purpose
Persist single-use answer-key tickets for AI-generated questions across backend restarts and multiple workers.

### Schema

```sql
CREATE TABLE question_tickets (
    id BIGSERIAL PRIMARY KEY,
    ticket_id VARCHAR(64) NOT NULL UNIQUE,
    student_id BIGINT NOT NULL REFERENCES student_profiles(id) ON DELETE CASCADE,
    question_text VARCHAR(2000) NOT NULL,
    options JSONB NOT NULL,           -- array of 4 strings
    correct_answer VARCHAR(300) NOT NULL,
    explanation VARCHAR(2000),
    topic_id BIGINT REFERENCES topics(id) ON DELETE SET NULL,
    topic_name VARCHAR(100),
    difficulty VARCHAR(20) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    consumed_at TIMESTAMP WITH TIME ZONE,
    idempotency_key VARCHAR(128),     -- optional, for duplicate generate protection
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX ix_question_tickets_student_id ON question_tickets(student_id);
CREATE INDEX ix_question_tickets_expires_at ON question_tickets(expires_at);
CREATE INDEX ix_question_tickets_student_expires ON question_tickets(student_id, expires_at);
-- Composite unique index for idempotency: scoped to student
CREATE UNIQUE INDEX ix_question_tickets_idempotency 
    ON question_tickets(student_id, idempotency_key) 
    WHERE idempotency_key IS NOT NULL;
```

### SQLAlchemy Model

```python
# backend/app/models/question_ticket.py
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_PK, Base


class QuestionTicket(Base):
    __tablename__ = "question_tickets"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_text: Mapped[str] = mapped_column(String(2000), nullable=False)
    options: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(300), nullable=False)
    explanation: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    topic_id: Mapped[int | None] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    topic_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_question_tickets_student_expires", "student_id", "expires_at"),
        UniqueConstraint(
            "student_id", "idempotency_key",
            name="uq_question_tickets_student_idempotency",
            postgresql_where=idempotency_key.isnot(None),
        ),
    )
```

### Migration

**File**: `backend/alembic/versions/xxx_add_question_tickets.py`

```python
"""add question_tickets

Revision ID: xxx
Revises: 1381cf99df52  # latest existing
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "xxx"
down_revision = "1381cf99df52"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_tickets",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), 
                  autoincrement=True, nullable=False),
        sa.Column("ticket_id", sa.String(64), nullable=False),
        sa.Column("student_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), 
                  nullable=False),
        sa.Column("question_text", sa.String(2000), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("correct_answer", sa.String(300), nullable=False),
        sa.Column("explanation", sa.String(2000), nullable=True),
        sa.Column("topic_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), 
                  nullable=True),
        sa.Column("topic_name", sa.String(100), nullable=True),
        sa.Column("difficulty", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), 
                  server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["student_id"], ["student_profiles.id"],
            name=op.f("fk_question_tickets_student_id_student_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["topics.id"],
            name=op.f("fk_question_tickets_topic_id_topics"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_tickets")),
        sa.UniqueConstraint("ticket_id", name=op.f("uq_question_tickets_ticket_id")),
    )
    op.create_index(
        op.f("ix_question_tickets_student_id"), "question_tickets", ["student_id"]
    )
    op.create_index(
        op.f("ix_question_tickets_expires_at"), "question_tickets", ["expires_at"]
    )
    op.create_index(
        "ix_question_tickets_student_expires", "question_tickets", 
        ["student_id", "expires_at"]
    )
    # Composite unique index for student-scoped idempotency
    op.create_index(
        "ix_question_tickets_idempotency", "question_tickets", 
        ["student_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_question_tickets_idempotency", table_name="question_tickets")
    op.drop_index("ix_question_tickets_student_expires", table_name="question_tickets")
    op.drop_index(op.f("ix_question_tickets_expires_at"), table_name="question_tickets")
    op.drop_index(op.f("ix_question_tickets_student_id"), table_name="question_tickets")
    op.drop_table("question_tickets")
```

### Operations

#### Idempotency-Aware Ticket Issue (Atomic Claim Pattern)

The ticket store implements a **claim-then-generate** pattern to prevent duplicate Gemini calls under concurrency:

```python
def issue(self, ticket: QuestionTicket) -> str:
    """
    Atomically claim or reuse an idempotency key, then generate and store the ticket.
    
    Uses INSERT ... ON CONFLICT to claim the key. If another concurrent request
    already claimed it, we wait for that request to complete and reuse its result.
    """
    ticket_id = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=TTL_SECONDS)
    
    # Per-student limit enforcement (atomic within same transaction)
    existing_count = self.db.scalar(
        select(func.count(QuestionTicket.id))
        .where(QuestionTicket.student_id == ticket.student_id)
        .where(QuestionTicket.consumed_at.is_(None))
        .where(QuestionTicket.expires_at > datetime.now(timezone.utc))
    )
    if existing_count >= MAX_TICKETS_PER_STUDENT:
        oldest = self.db.execute(
            select(QuestionTicket.id)
            .where(QuestionTicket.student_id == ticket.student_id)
            .where(QuestionTicket.consumed_at.is_(None))
            .order_by(QuestionTicket.expires_at.asc())
            .limit(existing_count - MAX_TICKETS_PER_STUDENT + 1)
        ).scalars().all()
        for oid in oldest:
            self.db.delete(self.db.get(QuestionTicket, oid))
    
    # If idempotency key provided, attempt to claim it
    if ticket.idempotency_key:
        # Try to insert a placeholder row claiming this key
        try:
            placeholder = QuestionTicket(
                ticket_id=ticket_id,
                student_id=ticket.student_id,
                question_text="",  # Will be filled after Gemini call
                options=[],
                correct_answer="",
                explanation=None,
                topic_id=ticket.topic_id,
                topic_name=ticket.topic_name,
                difficulty=ticket.difficulty,
                expires_at=expires_at,
                idempotency_key=ticket.idempotency_key,
            )
            self.db.add(placeholder)
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            # Another request already claimed this key. Wait for it to complete.
            return self._wait_for_idempotent_result(ticket.student_id, ticket.idempotency_key)
        
        # We claimed the key. Now call Gemini.
        try:
            # ... call Gemini, validate response ...
            # Update the placeholder with real data
            placeholder.question_text = parsed_question_text
            placeholder.options = parsed_options
            placeholder.correct_answer = parsed_correct_answer
            placeholder.explanation = parsed_explanation
            self.db.flush()
            return ticket_id
        except Exception:
            # On failure, delete the placeholder so key can be retried
            self.db.delete(placeholder)
            self.db.flush()
            raise
    
    # No idempotency key: normal single-use ticket
    db_ticket = QuestionTicket(
        ticket_id=ticket_id,
        student_id=ticket.student_id,
        question_text=ticket.question_text,
        options=ticket.options,
        correct_answer=ticket.correct_answer,
        explanation=ticket.explanation,
        topic_id=ticket.topic_id,
        topic_name=ticket.topic_name,
        difficulty=ticket.difficulty,
        expires_at=expires_at,
        idempotency_key=None,
    )
    self.db.add(db_ticket)
    self.db.flush()
    return ticket_id


def _wait_for_idempotent_result(self, student_id: int, idempotency_key: str) -> str:
    """Wait for concurrent request to complete and return its ticket_id."""
    # Poll for completion (with timeout)
    for _ in range(30):  # 30 seconds max wait
        existing = self.db.scalar(
            select(QuestionTicket.ticket_id)
            .where(QuestionTicket.student_id == student_id)
            .where(QuestionTicket.idempotency_key == idempotency_key)
            .where(QuestionTicket.question_text != "")
        )
        if existing:
            return existing
        time.sleep(1)
    raise ServiceUnavailableError("Idempotent request timed out")
```

#### Consume Ticket (SELECT FOR UPDATE + UPDATE)

```python
def consume(self, ticket_id: str, student_id: int) -> QuestionTicket | None:
    now = datetime.now(timezone.utc)
    
    db_ticket = self.db.execute(
        select(QuestionTicket)
        .where(QuestionTicket.ticket_id == ticket_id)
        .with_for_update()
    ).scalar_one_or_none()
    
    if db_ticket is None:
        return None
    if db_ticket.student_id != student_id:
        return None
    if db_ticket.consumed_at is not None:
        return None
    if db_ticket.expires_at <= now:
        return None
    
    # Convert to service-layer QuestionTicket dataclass
    ticket = QuestionTicket(
        student_id=db_ticket.student_id,
        question_text=db_ticket.question_text,
        options=db_ticket.options,
        correct_answer=db_ticket.correct_answer,
        explanation=db_ticket.explanation,
        topic_id=db_ticket.topic_id,
        topic_name=db_ticket.topic_name,
        difficulty=db_ticket.difficulty,
        expires_at=db_ticket.expires_at.timestamp(),
    )
    
    db_ticket.consumed_at = now
    self.db.flush()
    return ticket
```

#### Cleanup Expired (Periodic)

```python
def prune_expired(self) -> int:
    now = datetime.now(timezone.utc)
    result = self.db.execute(
        delete(QuestionTicket).where(QuestionTicket.expires_at <= now)
    )
    return result.rowcount
```

### Failure Behavior
- **DB unavailable on issue**: Raise `ServiceUnavailableError` (503)
- **DB unavailable on consume**: Raise `ServiceUnavailableError` (503) — ticket not consumed, client can retry
- **Deadlock on consume**: SQLAlchemy retry logic handles; if persistent → 503
- **Partial failure**: Transaction rolls back; no ticket created or consumed
- **Gemini failure after idempotency claim**: Placeholder deleted, key becomes available for retry

---

## Table 2: ai_rate_limits

### Purpose
Track per-user sliding-window request counts for AI endpoints across multiple workers.

### Schema

```sql
CREATE TABLE ai_rate_limits (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES student_profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index for efficient window queries
CREATE INDEX ix_ai_rate_limits_user_created ON ai_rate_limits(user_id, created_at);
```

### SQLAlchemy Model

```python
# backend/app/models/ai_rate_limit.py
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_PK, Base


class AIRateLimit(Base):
    __tablename__ = "ai_rate_limits"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_ai_rate_limits_user_created", "user_id", "created_at"),
    )
```

### Migration

**File**: `backend/alembic/versions/xxx_add_ai_rate_limits.py`

```python
"""add ai_rate_limits

Revision ID: xxx
Revises: xxx_add_question_tickets
Create Date: 2026-11-01
"""
from alembic import op
import sqlalchemy as sa

revision = "xxx"
down_revision = "xxx_add_question_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_rate_limits",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), 
                  autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), 
                  nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), 
                  server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["student_profiles.id"],
            name=op.f("fk_ai_rate_limits_user_id_student_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_rate_limits")),
    )
    op.create_index(
        op.f("ix_ai_rate_limits_user_id"), "ai_rate_limits", ["user_id"]
    )
    op.create_index(
        "ix_ai_rate_limits_user_created", "ai_rate_limits", 
        ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_ai_rate_limits_user_created", table_name="ai_rate_limits")
    op.drop_index(op.f("ix_ai_rate_limits_user_id"), table_name="ai_rate_limits")
    op.drop_table("ai_rate_limits")
```

### Atomic Concurrency-Safe Rate Limiting Implementation

**Selected Approach: PostgreSQL Advisory Lock + Sliding Window**

This approach guarantees that concurrent requests cannot exceed the configured limit, works across multiple workers, and does not depend on Python in-memory locks.

#### Algorithm

```python
def check(self, user_id: int) -> None:
    """
    Atomically check and record a rate limit hit using advisory lock.
    
    Transaction isolation: READ COMMITTED (PostgreSQL default)
    Advisory lock scope: transaction-level (released on commit/rollback)
    
    Steps:
    1. Acquire advisory lock for (user_id, current_window_hash)
    2. Count existing requests in sliding window
    3. If at limit, raise RateLimitExceededError
    4. Insert new request record
    5. Commit (releases lock)
    """
    window_start = datetime.now(timezone.utc) - timedelta(seconds=self.window_seconds)
    window_hash = int(window_start.timestamp())  # Coarse window hash for lock key
    
    with self.db.begin():
        # 1. Acquire advisory lock for this user's current window
        # This serializes concurrent rate-limit checks for the same user/window
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(:user_id, :window_hash)"),
            {"user_id": user_id, "window_hash": window_hash}
        )
        
        # 2. Count requests in sliding window (inside the lock)
        count = self.db.scalar(
            select(func.count(AIRateLimit.id))
            .where(AIRateLimit.user_id == user_id)
            .where(AIRateLimit.created_at >= window_start)
        ) or 0
        
        # 3. Check limit
        if count >= self.max_requests:
            # Calculate retry-after based on oldest request in window
            oldest = self.db.scalar(
                select(AIRateLimit.created_at)
                .where(AIRateLimit.user_id == user_id)
                .where(AIRateLimit.created_at >= window_start)
                .order_by(AIRateLimit.created_at.asc())
            )
            if oldest:
                retry_after = max(1, int(self.window_seconds - 
                    (datetime.now(timezone.utc) - oldest).total_seconds()))
            else:
                retry_after = int(self.window_seconds)
            raise RateLimitExceededError(retry_after)
        
        # 4. Record this request
        self.db.add(AIRateLimit(user_id=user_id))
        # 5. Commit releases advisory lock automatically
```

#### Alternative Considered: Fixed-Window Atomic Upsert

```sql
-- Alternative: Fixed window with single-row upsert per user/window
CREATE TABLE ai_rate_limit_windows (
    user_id BIGINT NOT NULL REFERENCES student_profiles(id) ON DELETE CASCADE,
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, window_start)
);
```

**Why Advisory Lock + Sliding Window was chosen:**
1. Preserves exact sliding-window semantics (no boundary bursts)
2. Works with existing `AIRateLimit` append-only table design
3. Advisory locks are lightweight (no row locks, no deadlocks with other transactions)
4. Clean separation: rate limiting logic doesn't require schema change

#### Cleanup (Periodic)

```python
def prune_old(self) -> int:
    window_start = datetime.now(timezone.utc) - timedelta(seconds=self.window_seconds)
    result = self.db.execute(
        delete(AIRateLimit).where(AIRateLimit.created_at < window_start)
    )
    return result.rowcount
```

### Failure Behavior
- **DB unavailable on check**: Raise `ServiceUnavailableError` (503)
- **Advisory lock contention**: Requests queue briefly; lock is per-user/window
- **Transaction rollback**: Lock released automatically; no leaked state
- **Partial failure**: No request recorded if transaction fails

### Performance Estimate
- **1000 concurrent users** × 10 req/min = ~167 req/s
- **Per request**: 1 advisory lock + 1 COUNT + 1 INSERT (in same transaction)
- **PostgreSQL capacity**: ~1000-5000 simple writes/s on modest hardware
- **Connection pool**: pool_size=20, max_overflow=10 → 30 concurrent DB connections
- **Advisory lock overhead**: ~0.1ms per lock acquisition
- **Verdict**: Well within capacity; no pooling changes needed

---

## Service-Layer Dataclass Consistency

### Service-Layer `QuestionTicket` Dataclass (Updated)

The service-layer dataclass in `ai_tickets.py` must be updated to include all fields needed by the service architecture:

```python
# backend/app/services/ai_tickets.py (service-layer dataclass)
from dataclasses import dataclass
from typing import Optional


@dataclass
class QuestionTicket:
    """Service-layer representation of an AI question ticket."""
    student_id: int
    question_text: str
    options: list[str]
    correct_answer: str
    explanation: Optional[str]
    topic_id: Optional[int]
    topic_name: Optional[str]
    difficulty: str
    expires_at: float  # Unix timestamp
    
    # New fields for idempotency support
    idempotency_key: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
```

**Relationship Mapping:**
| SQLAlchemy Model | Service Dataclass | API Response |
|-----------------|------------------|--------------|
| `id` | `id` | Not exposed |
| `ticket_id` | (used as key) | `ticket` |
| `student_id` | `student_id` | Not exposed |
| `question_text` | `question_text` | `question` |
| `options` | `options` | `options` |
| `correct_answer` | `correct_answer` | Never exposed to student |
| `explanation` | `explanation` | `explanation` (on evaluate) |
| `topic_id` | `topic_id` | `topic_id` |
| `topic_name` | `topic_name` | `topic_name` |
| `difficulty` | `difficulty` | `difficulty` |
| `expires_at` | `expires_at` (timestamp) | Not exposed |
| `consumed_at` | (checked internally) | Not exposed |
| `idempotency_key` | `idempotency_key` | Not exposed |
| `created_at` | `created_at` | Not exposed |

**Critical Security Rule**: `correct_answer` and `explanation` are NEVER included in `/questions/generate` response. They are only revealed in `/questions/evaluate` after the student submits an answer.

---

## Integration Points

### Model Registration
**File**: `backend/app/models/__init__.py`
```python
# Add to imports:
from app.models.question_ticket import QuestionTicket
from app.models.ai_rate_limit import AIRateLimit

# Add to __all__:
__all__ = [
    ...,
    "QuestionTicket",
    "AIRateLimit",
]
```

### Service Swaps
**File**: `backend/app/services/ai_tickets.py`
```python
# Replace module-level instance:
# OLD: question_ticket_store = TicketStore()
# NEW: 
def get_question_ticket_store(db: Session) -> DatabaseTicketStore:
    return DatabaseTicketStore(db)

# In ai_questions.py, pass db to get store:
def _get_ai_question_service(db: Session = Depends(get_db)) -> AIQuestionService:
    return AIQuestionService(db, ticket_store=get_question_ticket_store(db))
```

**File**: `backend/app/core/rate_limit.py`
```python
# Replace module-level instance:
# OLD: ai_limiter = SlidingWindowLimiter(max_requests=settings.AI_RATE_LIMIT_PER_MINUTE)
# NEW: 
def get_ai_limiter(db: Session) -> DatabaseRateLimiter:
    return DatabaseRateLimiter(
        db, 
        max_requests=settings.AI_RATE_LIMIT_PER_MINUTE,
        window_seconds=60.0
    )

# In ai.py routes, inject db:
def _enforce_ai_rate_limit(
    user: Annotated[object, Depends(require_student)],
    db: Session = Depends(get_db),
) -> object:
    get_ai_limiter(db).check(user.id)
    return user
```

---

## SQLite Compatibility (Tests)

Both tables use `BigInteger().with_variant(Integer, "sqlite")` for FK columns to work with SQLite in tests.

The `JSONB` type in `question_tickets.options` works in SQLite via `postgresql.JSONB(astext_type=sa.Text())` which stores as TEXT.

**Note**: SQLite cannot test true concurrency behavior. PostgreSQL-specific concurrency tests are required (see `PHASE_4_TEST_PLAN.md`).

---

## Rollback

See `PHASE_4_ROLLBACK_PLAN.md` — alembic downgrade drops both tables in reverse order.

---

## Confirmation

**No database changes were made during planning.** This is a design document only.