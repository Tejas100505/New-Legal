"""add_status_history_table

Revision ID: b2c3d4e5f6a7
Revises: e8f9a0b1c2d3
Create Date: 2026-09-27 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'e8f9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'status_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('old_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('changed_by', sa.UUID(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_status_history_id'), 'status_history', ['id'], unique=False)
    op.create_index(op.f('ix_status_history_document_id'), 'status_history', ['document_id'], unique=False)
    op.create_index(op.f('ix_status_history_changed_at'), 'status_history', ['changed_at'], unique=False)
    op.create_index(op.f('ix_status_history_new_status'), 'status_history', ['new_status'], unique=False)
    op.create_index(op.f('ix_status_history_changed_by'), 'status_history', ['changed_by'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_status_history_changed_by'), table_name='status_history')
    op.drop_index(op.f('ix_status_history_new_status'), table_name='status_history')
    op.drop_index(op.f('ix_status_history_changed_at'), table_name='status_history')
    op.drop_index(op.f('ix_status_history_document_id'), table_name='status_history')
    op.drop_index(op.f('ix_status_history_id'), table_name='status_history')
    op.drop_table('status_history')
