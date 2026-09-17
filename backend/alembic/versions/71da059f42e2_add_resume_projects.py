"""add resume projects

Revision ID: 71da059f42e2
Revises: e7b3c9a2f614
Create Date: 2026-09-17 18:58:06.939812

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71da059f42e2'
down_revision: Union[str, Sequence[str], None] = 'e7b3c9a2f614'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'resume_analyses',
        sa.Column('projects', sa.JSON(), nullable=True),
    )
    op.execute(sa.text(
        "UPDATE resume_analyses SET projects = JSON_ARRAY() WHERE projects IS NULL"
    ))
    if op.get_bind().dialect.name == 'sqlite':
        with op.batch_alter_table('resume_analyses') as batch:
            batch.alter_column(
                'projects', existing_type=sa.JSON(), nullable=False
            )
    else:
        op.alter_column(
            'resume_analyses', 'projects', existing_type=sa.JSON(), nullable=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('resume_analyses', 'projects')
