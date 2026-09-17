"""add lead pros and cons

Revision ID: e7b3c9a2f614
Revises: c61ab78d4e20
Create Date: 2026-09-17 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7b3c9a2f614'
down_revision: Union[str, Sequence[str], None] = 'c61ab78d4e20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 岗位池每行显示的「合适 / 不合适」标签，打分时一起算好存下来
    op.add_column('job_leads', sa.Column('pros', sa.JSON(), nullable=True))
    op.add_column('job_leads', sa.Column('cons', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('job_leads', 'cons')
    op.drop_column('job_leads', 'pros')
