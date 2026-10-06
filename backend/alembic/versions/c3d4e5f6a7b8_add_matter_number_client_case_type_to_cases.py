"""add_matter_number_client_case_type_to_cases

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-04 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('cases', sa.Column('matter_number', sa.String(length=100), nullable=True))
    op.add_column('cases', sa.Column('client', sa.String(length=255), nullable=True))
    op.add_column('cases', sa.Column('case_type', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_cases_matter_number'), 'cases', ['matter_number'], unique=False)
    op.create_index(op.f('ix_cases_client'), 'cases', ['client'], unique=False)
    op.create_index(op.f('ix_cases_case_type'), 'cases', ['case_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_cases_case_type'), table_name='cases')
    op.drop_index(op.f('ix_cases_client'), table_name='cases')
    op.drop_index(op.f('ix_cases_matter_number'), table_name='cases')
    op.drop_column('cases', 'case_type')
    op.drop_column('cases', 'client')
    op.drop_column('cases', 'matter_number')
