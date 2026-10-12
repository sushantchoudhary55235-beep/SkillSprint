"""Add bookmarks table (Feature Group 12 — Saved Questions).

Additive, backward-compatible change: one new table, no modification to any
existing column. Revision chain: b7c21d9e4f10 → c3d84e6a9b12.
"""
from alembic import op
import sqlalchemy as sa

revision = "c3d84e6a9b12"
down_revision = "b7c21d9e4f10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bookmarks",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("bookmark_type", sa.String(length=20), nullable=False, index=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("problem_id", sa.Integer(), sa.ForeignKey("coding_problems.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("student_id", "bookmark_type", "question_id", "problem_id", name="uq_bookmark_target"),
    )


def downgrade() -> None:
    op.drop_table("bookmarks")
