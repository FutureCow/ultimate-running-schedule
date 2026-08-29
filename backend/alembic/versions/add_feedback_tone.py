"""add feedback_tone to users and plans

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-08-29

users.feedback_tone is the athlete's default; plans.feedback_tone overrides it
per plan and is NULL when the plan just follows the profile.
"""
from alembic import op
import sqlalchemy as sa

revision = 'b7c8d9e0f1a2'
down_revision = 'a6b7c8d9e0f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('feedback_tone', sa.String(length=20), nullable=False, server_default='scientific'),
    )
    op.add_column('plans', sa.Column('feedback_tone', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('plans', 'feedback_tone')
    op.drop_column('users', 'feedback_tone')
