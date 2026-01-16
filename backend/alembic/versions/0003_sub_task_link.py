"""add subscription_id to tasks

Revision ID: 0003_sub_task_link
Revises: 0002_report_lang_subs
Create Date: 2026-01-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_sub_task_link"
down_revision = "0002_report_lang_subs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("subscription_id", sa.UUID(), nullable=True))
    op.create_index("ix_tasks_subscription_id", "tasks", ["subscription_id"])
    op.create_foreign_key(
        "fk_tasks_subscription_id",
        "tasks",
        "subscriptions",
        ["subscription_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_tasks_subscription_id", "tasks", type_="foreignkey")
    op.drop_index("ix_tasks_subscription_id", table_name="tasks")
    op.drop_column("tasks", "subscription_id")
