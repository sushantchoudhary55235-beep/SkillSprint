"""add ai_answer_logs

Revision ID: a1f29c4d7e03
Revises: fb9deee76814
Create Date: 2026-09-21

Phase 15C: record only the outcome of answering AI-generated questions
(never the question text).
"""
from alembic import op
import sqlalchemy as sa

revision = "a1f29c4d7e03"
down_revision = "fb9deee76814"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_answer_logs",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("student_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("topic_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("topic_name", sa.String(length=100), nullable=True),
        sa.Column("difficulty", sa.String(length=20), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("time_taken_seconds", sa.Integer(), nullable=True),
        sa.Column("xp_earned", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["student_profiles.id"],
            name=op.f("fk_ai_answer_logs_student_id_student_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_ai_answer_logs_topic_id_topics"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_answer_logs")),
    )
    op.create_index(
        op.f("ix_ai_answer_logs_student_id"), "ai_answer_logs", ["student_id"], unique=False
    )
    op.create_index(
        op.f("ix_ai_answer_logs_topic_id"), "ai_answer_logs", ["topic_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_answer_logs_topic_id"), table_name="ai_answer_logs")
    op.drop_index(op.f("ix_ai_answer_logs_student_id"), table_name="ai_answer_logs")
    op.drop_table("ai_answer_logs")
