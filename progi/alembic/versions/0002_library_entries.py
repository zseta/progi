"""library entries

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "library_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("playbook", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # SQLite doesn't support ADD CONSTRAINT; use batch mode (copy-and-move).
    with op.batch_alter_table("steps") as batch_op:
        batch_op.add_column(sa.Column("library_entry_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_steps_library_entry_id",
            "library_entries",
            ["library_entry_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("steps") as batch_op:
        batch_op.drop_constraint("fk_steps_library_entry_id", type_="foreignkey")
        batch_op.drop_column("library_entry_id")
    op.drop_table("library_entries")
