"""add job targets

Revision ID: 5d2c8a1e9f47
Revises: 08e73e523d30
Create Date: 2026-09-15 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d2c8a1e9f47'
down_revision: Union[str, Sequence[str], None] = '08e73e523d30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('job_targets', sa.JSON(), nullable=True))
    op.add_column('job_leads', sa.Column('target', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('job_leads', 'target')
    op.drop_column('users', 'job_targets')
