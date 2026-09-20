"""add_quota_paused_status

Revision ID: d7e8f9a0b1c2
Revises: fcf4df5ac838
Create Date: 2026-09-13 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, None] = 'fcf4df5ac838'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_STATUSES = (
    'UPLOADED', 'VALIDATING', 'OCR_PROCESSING', 'CHUNKING',
    'EMBEDDING', 'ANALYZING', 'REVIEWED', 'FLAGGED', 'QUOTA_PAUSED', 'ERROR',
    'uploaded', 'validating', 'ocr_processing', 'chunking',
    'embedding', 'analyzing', 'reviewed', 'flagged', 'quota_paused', 'error'
)

OLD_STATUSES = (
    'UPLOADED', 'VALIDATING', 'OCR_PROCESSING', 'CHUNKING',
    'EMBEDDING', 'ANALYZING', 'REVIEWED', 'FLAGGED', 'ERROR',
    'uploaded', 'validating', 'ocr_processing', 'chunking',
    'embedding', 'analyzing', 'reviewed', 'flagged', 'error'
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # Drop existing check constraint if present and re-create with quota_paused
        op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS document_status")
        status_list = ", ".join(f"'{s}'" for s in NEW_STATUSES)
        op.execute(f"ALTER TABLE documents ADD CONSTRAINT document_status CHECK (status IN ({status_list}))")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS document_status")
        status_list = ", ".join(f"'{s}'" for s in OLD_STATUSES)
        op.execute(f"ALTER TABLE documents ADD CONSTRAINT document_status CHECK (status IN ({status_list}))")
