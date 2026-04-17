"""add extra_notes to plans

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-04-17

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('plans', sa.Column('extra_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('plans', 'extra_notes')
