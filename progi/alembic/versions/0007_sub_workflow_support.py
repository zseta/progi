"""add sub-workflow support: workflow playbook, steps.sub_workflow_id, step_instances.sub_workflow_step_id

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # workflows.playbook — skip if already exists (can happen from a partial prior run)
    existing_wf_cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(workflows)")).fetchall()}
    if "playbook" not in existing_wf_cols:
        with op.batch_alter_table("workflows") as batch_op:
            batch_op.add_column(sa.Column("playbook", sa.Text(), nullable=True))

    existing_step_cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(steps)")).fetchall()}
    if "sub_workflow_id" not in existing_step_cols:
        with op.batch_alter_table("steps") as batch_op:
            batch_op.add_column(sa.Column("sub_workflow_id", sa.Integer(), nullable=True))

    existing_si_cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(step_instances)")).fetchall()}
    if "sub_workflow_step_id" not in existing_si_cols:
        with op.batch_alter_table("step_instances") as batch_op:
            batch_op.add_column(sa.Column("sub_workflow_step_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("step_instances") as batch_op:
        batch_op.drop_column("sub_workflow_step_id")

    with op.batch_alter_table("steps") as batch_op:
        batch_op.drop_column("sub_workflow_id")

    with op.batch_alter_table("workflows") as batch_op:
        batch_op.drop_column("playbook")
