"""add_is_system_fixture_to_cases

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-05 07:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRIMARY_CASE_ID = '8d8389d4-2534-452d-85b4-65efe5b8e1c3'


def upgrade() -> None:
    # 1. Add column is_system_fixture with server default false
    op.add_column(
        'cases',
        sa.Column('is_system_fixture', sa.Boolean(), server_default=sa.text('false'), nullable=False)
    )
    op.create_index(op.f('ix_cases_is_system_fixture'), 'cases', ['is_system_fixture'], unique=False)

    # 2. Backfill: classify existing cases
    # The primary California case (8d8389d4-2534-452d-85b4-65efe5b8e1c3) is the real legal matter (is_system_fixture = false).
    # All 437 other legacy test/integration fixture cases are classified as system fixtures (is_system_fixture = true).
    op.execute(
        f"UPDATE cases SET is_system_fixture = true WHERE id != '{PRIMARY_CASE_ID}'"
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_cases_is_system_fixture'), table_name='cases')
    op.drop_column('cases', 'is_system_fixture')
