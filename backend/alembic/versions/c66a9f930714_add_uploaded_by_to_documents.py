"""add_uploaded_by_to_documents

Revision ID: c66a9f930714
Revises: e3e13670cc14
Create Date: 2026-09-06 14:45:02.649581

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c66a9f930714'
down_revision: Union[str, None] = 'e3e13670cc14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add uploaded_by column to documents table
    op.add_column('documents', sa.Column('uploaded_by', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_documents_uploaded_by_users',
        'documents',
        'users',
        ['uploaded_by'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(op.f('ix_documents_uploaded_by'), 'documents', ['uploaded_by'], unique=False)

    # 2. Backfill existing documents: assign to primary system/admin user if one exists
    connection = op.get_bind()
    result = connection.execute(
        sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
    ).fetchone()
    if result and result[0]:
        connection.execute(
            sa.text("UPDATE documents SET uploaded_by = :uid WHERE uploaded_by IS NULL"),
            {"uid": result[0]},
        )


def downgrade() -> None:
    op.drop_index(op.f('ix_documents_uploaded_by'), table_name='documents')
    op.drop_constraint('fk_documents_uploaded_by_users', 'documents', type_='foreignkey')
    op.drop_column('documents', 'uploaded_by')
