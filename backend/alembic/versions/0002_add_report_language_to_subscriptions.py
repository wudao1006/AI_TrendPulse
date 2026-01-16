"""add report_language to subscriptions

Revision ID: 0002_report_lang_subs
Revises: 0001_add_report_language
Create Date: 2026-01-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_report_lang_subs"
down_revision = "0001_add_report_language"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column("report_language", sa.String(length=10), nullable=True))
    op.execute("UPDATE subscriptions SET report_language = 'auto' WHERE report_language IS NULL")
    op.alter_column("subscriptions", "report_language", nullable=False)


def downgrade() -> None:
    op.drop_column("subscriptions", "report_language")
