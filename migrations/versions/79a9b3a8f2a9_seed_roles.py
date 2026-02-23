"""seed roles

Revision ID: 79a9b3a8f2a9
Revises: d6d1f6d25483
Create Date: 2026-02-07 17:56:08.949342

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79a9b3a8f2a9'
down_revision: Union[str, Sequence[str], None] = 'd6d1f6d25483'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    INSERT INTO roles (id, name) VALUES
      (1, 'participant'),
      (2, 'org_committee'),
      (3, 'admin')
    ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
    DELETE FROM roles
    WHERE id IN (1, 2, 3);
    """)
