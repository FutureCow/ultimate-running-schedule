"""add max_hr to users

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-04-29

"""
from alembic import op
import sqlalchemy as sa

revision = 'c2d3e4f5a6b7'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('max_hr', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'max_hr')
