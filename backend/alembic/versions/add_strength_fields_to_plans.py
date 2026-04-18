"""add strength fields to plans

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('plans', sa.Column('strength_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('plans', sa.Column('strength_location', sa.String(50), nullable=True))
    op.add_column('plans', sa.Column('strength_type', sa.String(50), nullable=True))
    op.add_column('plans', sa.Column('strength_days', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('plans', 'strength_days')
    op.drop_column('plans', 'strength_type')
    op.drop_column('plans', 'strength_location')
    op.drop_column('plans', 'strength_enabled')
