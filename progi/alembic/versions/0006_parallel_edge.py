"""add parallel column to step_edges

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("step_edges") as batch_op:
        batch_op.add_column(
            sa.Column("parallel", sa.Boolean(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    with op.batch_alter_table("step_edges") as batch_op:
        batch_op.drop_column("parallel")
