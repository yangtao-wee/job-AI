"""add lead jd hits

Revision ID: c61ab78d4e20
Revises: 9a4e6b2c1d38
Create Date: 2026-09-15 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c61ab78d4e20'
down_revision: Union[str, Sequence[str], None] = '9a4e6b2c1d38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('job_leads', sa.Column('jd_hits', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('job_leads', 'jd_hits')
