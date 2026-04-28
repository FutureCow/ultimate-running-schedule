"""add user tier and session ai_feedback

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('tier', sa.String(20), nullable=False, server_default='elite'))
    op.add_column('workout_sessions', sa.Column('ai_feedback', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('workout_sessions', 'ai_feedback')
    op.drop_column('users', 'tier')
