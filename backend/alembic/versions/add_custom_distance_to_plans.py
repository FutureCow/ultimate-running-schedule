"""add custom_distance_km and goal_kind to plans

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-08-29

"""
from alembic import op
import sqlalchemy as sa

revision = 'a6b7c8d9e0f1'
down_revision = 'f5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('plans', sa.Column('custom_distance_km', sa.Float(), nullable=True))
    op.add_column(
        'plans',
        sa.Column('goal_kind', sa.String(length=20), nullable=False, server_default='race'),
    )


def downgrade() -> None:
    op.drop_column('plans', 'goal_kind')
    op.drop_column('plans', 'custom_distance_km')
