"""Gamification integrity constraints + daily mission date-scoping.

Revision ID: b7c21d9e4f10
Revises: a1f29c4d7e03
Create Date: 2026-09-22

- xp_transactions: unique (student_id, activity_type, reference_id) so a
  concurrent duplicate event can never double-reward XP (DB-level idempotency).
- student_missions: assigned_date column + unique (student, mission, date) so
  DAILY missions actually reset each day (one row per day).

SQLite notes: constraints are added via batch mode (copy-and-move), and the
xp dedupe runs before the constraint so legacy duplicate rows don't block it.
"""
from alembic import op
import sqlalchemy as sa

revision = "b7c21d9e4f10"
down_revision = "a1f29c4d7e03"
branch_labels = None
depends_on = None


def _dedupe_xp() -> None:
    """Keep the earliest row per (student, activity_type, reference_id)."""
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        bind.execute(sa.text(
            "DELETE FROM xp_transactions WHERE id NOT IN ("
            "  SELECT MIN(id) FROM xp_transactions"
            "  GROUP BY student_id, activity_type, reference_id)"
        ))
    else:
        bind.execute(sa.text(
            "DELETE FROM xp_transactions t USING xp_transactions keep "
            "WHERE t.student_id = keep.student_id "
            "AND t.activity_type = keep.activity_type "
            "AND t.reference_id IS NOT DISTINCT FROM keep.reference_id "
            "AND t.id > keep.id"
        ))


def upgrade() -> None:
    # --- student_missions.assigned_date (daily scoping) ----------------
    op.add_column("student_missions", sa.Column("assigned_date", sa.Date(), nullable=True))
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        bind.execute(sa.text(
            "UPDATE student_missions SET assigned_date = "
            "COALESCE(DATE(completed_at), DATE(started_at), DATE('now'))"
        ))
    else:
        bind.execute(sa.text(
            "UPDATE student_missions SET assigned_date = "
            "COALESCE(CAST(completed_at AS DATE), CAST(started_at AS DATE), CURRENT_DATE)"
        ))
    op.create_index(
        "ix_student_missions_assigned_date", "student_missions", ["assigned_date"]
    )
    with op.batch_alter_table("student_missions") as batch:
        batch.create_unique_constraint(
            "uq_student_mission_day", ["student_id", "mission_id", "assigned_date"]
        )

    # --- xp_transactions idempotency -----------------------------------
    _dedupe_xp()
    with op.batch_alter_table("xp_transactions") as batch:
        batch.create_unique_constraint(
            "uq_xp_event", ["student_id", "activity_type", "reference_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("xp_transactions") as batch:
        batch.drop_constraint("uq_xp_event", type_="unique")
    with op.batch_alter_table("student_missions") as batch:
        batch.drop_constraint("uq_student_mission_day", type_="unique")
    op.drop_index("ix_student_missions_assigned_date", table_name="student_missions")
    op.drop_column("student_missions", "assigned_date")
