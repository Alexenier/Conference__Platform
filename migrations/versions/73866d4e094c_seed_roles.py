"""seed roles

Revision ID: 73866d4e094c
Revises: f54fa48bf2ce
Create Date: 2026-02-07 17:34:11.049474

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '73866d4e094c'
down_revision: Union[str, Sequence[str], None] = 'f54fa48bf2ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
