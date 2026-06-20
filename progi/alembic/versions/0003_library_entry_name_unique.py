"""unique constraint on library_entries.name

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-20
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("library_entries") as batch_op:
        batch_op.create_unique_constraint("uq_library_entries_name", ["name"])


def downgrade() -> None:
    with op.batch_alter_table("library_entries") as batch_op:
        batch_op.drop_constraint("uq_library_entries_name", type_="unique")
