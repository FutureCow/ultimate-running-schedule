"""add race_date to plans

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-17

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('plans', sa.Column('race_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('plans', 'race_date')
