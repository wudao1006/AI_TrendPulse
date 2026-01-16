"""add report_language to tasks

Revision ID: 0001_add_report_language
Revises: 
Create Date: 2026-01-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_add_report_language"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("report_language", sa.String(length=10), nullable=True))
    op.execute("UPDATE tasks SET report_language = 'auto' WHERE report_language IS NULL")
    op.alter_column("tasks", "report_language", nullable=False)


def downgrade() -> None:
    op.drop_column("tasks", "report_language")
