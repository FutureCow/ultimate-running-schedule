"""add weekly_review to plans

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-09-30

The latest weekly review of a plan under way: the numbers, and for Elite the
narrative written from them.
"""
from alembic import op
import sqlalchemy as sa

revision = 'e0f1a2b3c4d5'
down_revision = 'd9e0f1a2b3c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('plans', sa.Column('weekly_review', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('plans', 'weekly_review')
