"""add garmin_activities cache table

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa

revision = 'f5a6b7c8d9e0'
down_revision = 'e4f5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'garmin_activities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('activity_id', sa.String(100), nullable=False),
        sa.Column('activity_name', sa.String(255)),
        sa.Column('activity_type', sa.String(50)),
        sa.Column('start_time', sa.DateTime(timezone=True)),
        sa.Column('distance_km', sa.Float()),
        sa.Column('duration_seconds', sa.Integer()),
        sa.Column('avg_pace_per_km', sa.String(20)),
        sa.Column('avg_heart_rate', sa.Integer()),
        sa.Column('max_heart_rate', sa.Integer()),
        sa.Column('avg_cadence', sa.Integer()),
        sa.Column('elevation_gain_m', sa.Float()),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'activity_id', name='uq_user_activity'),
    )
    op.create_index('ix_garmin_activities_user_id', 'garmin_activities', ['user_id'])
    op.create_index('ix_garmin_activities_start_time', 'garmin_activities', ['start_time'])


def downgrade() -> None:
    op.drop_table('garmin_activities')
