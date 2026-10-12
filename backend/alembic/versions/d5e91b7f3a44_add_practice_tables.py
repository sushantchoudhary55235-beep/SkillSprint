"""Create missing practice_sessions / practice_answers tables.

Corrective migration: the practice model (app/models/practice.py) was added
after the initial schema, but no migration ever created its tables — the test
suite hid the gap because it uses Base.metadata.create_all() rather than
alembic. Any fresh `alembic upgrade head` deployment followed by the practice
flow would have crashed with "no such table".

Backward compatible: additive only. Guarded with inspector checks so databases
where the tables already exist (e.g. created via create_all) are untouched.

Revision chain: c3d84e6a9b12 -> d5e91b7f3a44
"""
from alembic import op
import sqlalchemy as sa

revision = "d5e91b7f3a44"
down_revision = "c3d84e6a9b12"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "practice_sessions"):
        op.create_table(
            "practice_sessions",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("mode", sa.String(length=20), nullable=False, server_default="TOPIC"),
            sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id"), nullable=True, index=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True, index=True),
            sa.Column("difficulty", sa.String(length=20), nullable=True),
            sa.Column("question_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("incorrect_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("unattempted_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("score", sa.Integer(), nullable=True),
            sa.Column("xp_earned", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_time_seconds", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="IN_PROGRESS", index=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_table(inspector, "practice_answers"):
        op.create_table(
            "practice_answers",
            sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.Integer(), sa.ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False, index=True),
            sa.Column("selected_option_id", sa.Integer(), sa.ForeignKey("question_options.id"), nullable=True),
            sa.Column("is_correct", sa.Boolean(), nullable=True),
            sa.Column("time_taken_seconds", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "practice_answers" in inspector.get_table_names():
        op.drop_table("practice_answers")
    if "practice_sessions" in inspector.get_table_names():
        op.drop_table("practice_sessions")
