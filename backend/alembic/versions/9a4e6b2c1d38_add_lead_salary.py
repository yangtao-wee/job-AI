"""add lead salary

Revision ID: 9a4e6b2c1d38
Revises: 5d2c8a1e9f47
Create Date: 2026-09-15 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a4e6b2c1d38'
down_revision: Union[str, Sequence[str], None] = '5d2c8a1e9f47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('job_leads', sa.Column('salary', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('job_leads', 'salary')
