"""drop input_spec and output_spec from steps

Revision ID: 0005
Revises: 4643697c3984
Create Date: 2026-06-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "4643697c3984"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("steps") as batch_op:
        batch_op.drop_column("input_spec")
        batch_op.drop_column("output_spec")


def downgrade() -> None:
    with op.batch_alter_table("steps") as batch_op:
        batch_op.add_column(sa.Column("input_spec", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("output_spec", sa.JSON(), nullable=True))
