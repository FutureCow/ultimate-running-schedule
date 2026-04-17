"""add profile fields to users

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-17

"""
from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('age', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('height_cm', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('weight_kg', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('weekly_km', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('weekly_runs', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('injuries', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'injuries')
    op.drop_column('users', 'weekly_runs')
    op.drop_column('users', 'weekly_km')
    op.drop_column('users', 'weight_kg')
    op.drop_column('users', 'height_cm')
    op.drop_column('users', 'age')
