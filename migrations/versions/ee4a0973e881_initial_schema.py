"""add disputes table

Revision ID: ee4a0973e881
Revises: aa7c20024f53
Create Date: 2026-06-14 16:10:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'ee4a0973e881'
down_revision = 'aa7c20024f53'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'disputes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('check_id', sa.String(length=48), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('resolution', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('disputes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_disputes_check_id'), ['check_id'], unique=False)


def downgrade():
    with op.batch_alter_table('disputes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_disputes_check_id'))
    op.drop_table('disputes')
