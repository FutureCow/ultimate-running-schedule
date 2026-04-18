"""add public_id to plans

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-18
"""
from alembic import op
import sqlalchemy as sa
import uuid

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add column as nullable first so existing rows don't violate the constraint
    op.add_column('plans', sa.Column('public_id', sa.String(36), nullable=True))

    # Backfill existing rows with a unique UUID each
    conn = op.get_bind()
    plans = conn.execute(sa.text("SELECT id FROM plans")).fetchall()
    for (plan_id,) in plans:
        conn.execute(
            sa.text("UPDATE plans SET public_id = :uid WHERE id = :id"),
            {"uid": str(uuid.uuid4()), "id": plan_id},
        )

    # Now make it non-nullable and add unique index
    op.alter_column('plans', 'public_id', nullable=False)
    op.create_unique_constraint('uq_plans_public_id', 'plans', ['public_id'])
    op.create_index('ix_plans_public_id', 'plans', ['public_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_plans_public_id', table_name='plans')
    op.drop_constraint('uq_plans_public_id', 'plans', type_='unique')
    op.drop_column('plans', 'public_id')
