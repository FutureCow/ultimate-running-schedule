"""add warmup_km and cooldown_km to workout_sessions

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-09-10

Garmin workouts hardcoded a 1 km warm-up and a 500 m cool-down regardless of
what the plan described. These columns let the plan say.
"""
from alembic import op
import sqlalchemy as sa

revision = 'c8d9e0f1a2b3'
down_revision = 'b7c8d9e0f1a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('workout_sessions', sa.Column('warmup_km', sa.Float(), nullable=True))
    op.add_column('workout_sessions', sa.Column('cooldown_km', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('workout_sessions', 'cooldown_km')
    op.drop_column('workout_sessions', 'warmup_km')
