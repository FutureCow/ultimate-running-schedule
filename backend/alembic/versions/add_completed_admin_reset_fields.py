"""add completed/admin/reset fields

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-04-18
"""
from alembic import op
import sqlalchemy as sa

revision = 'a7b8c9d0e1f2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # workout_sessions: completed_at + garmin_activity_id
    op.add_column('workout_sessions', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('workout_sessions', sa.Column('garmin_activity_id', sa.String(100), nullable=True))

    # users: is_admin + password reset fields
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('password_reset_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('workout_sessions', 'completed_at')
    op.drop_column('workout_sessions', 'garmin_activity_id')
    op.drop_column('users', 'is_admin')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'password_reset_expires')
