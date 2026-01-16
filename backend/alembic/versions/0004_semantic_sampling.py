"""add semantic_sampling to tasks and subscriptions

Revision ID: 0004_semantic_sampling
Revises: 0003_sub_task_link
Create Date: 2026-01-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0004_semantic_sampling"
down_revision = "0003_sub_task_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("semantic_sampling", sa.Boolean(), nullable=True))
    op.execute("UPDATE tasks SET semantic_sampling = FALSE WHERE semantic_sampling IS NULL")
    op.alter_column("tasks", "semantic_sampling", nullable=False)

    op.add_column("subscriptions", sa.Column("semantic_sampling", sa.Boolean(), nullable=True))
    op.execute("UPDATE subscriptions SET semantic_sampling = FALSE WHERE semantic_sampling IS NULL")
    op.alter_column("subscriptions", "semantic_sampling", nullable=False)


def downgrade() -> None:
    op.drop_column("subscriptions", "semantic_sampling")
    op.drop_column("tasks", "semantic_sampling")
