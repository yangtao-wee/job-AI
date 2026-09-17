"""add lead jd screening

Revision ID: 08e73e523d30
Revises: 6c9b1faaa5a8
Create Date: 2026-09-14 16:09:30.086574

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08e73e523d30'
down_revision: Union[str, Sequence[str], None] = '6c9b1faaa5a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('job_leads', sa.Column('base_score', sa.Integer(), nullable=True))
    op.add_column('job_leads', sa.Column('jd_flags', sa.JSON(), nullable=True))
    op.add_column('job_leads', sa.Column('jd_cut', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('job_leads', 'jd_cut')
    op.drop_column('job_leads', 'jd_flags')
    op.drop_column('job_leads', 'base_score')
