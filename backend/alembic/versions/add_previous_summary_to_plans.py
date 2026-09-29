"""add previous_summary to plans

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-09-30

A follow-up plan stores a snapshot of the plan it builds on, so the context
survives that plan being deleted and is kept when the follow-up is regenerated.
"""
from alembic import op
import sqlalchemy as sa

revision = 'd9e0f1a2b3c4'
down_revision = 'c8d9e0f1a2b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('plans', sa.Column('previous_summary', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('plans', 'previous_summary')
