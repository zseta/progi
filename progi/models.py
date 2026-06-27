"""SQLAlchemy Core table definitions (the database schema).

This module is the single source of truth for the schema. It is imported by
``db.py`` (queries/mutations) and by Alembic (autogenerate migrations).

``input_data`` / ``output`` are JSON columns on step_instances:
SQLAlchemy serialises dicts to TEXT on write and parses them back on read, so
the Python side always deals in plain dicts (no manual json.dumps/loads).
"""

from __future__ import annotations

import sqlalchemy as sa

metadata = sa.MetaData()

workflows = sa.Table(
    "workflows",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("name", sa.String(255), nullable=False),
    sa.Column("description", sa.Text),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
)

steps = sa.Table(
    "steps",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column(
        "workflow_id",
        sa.Integer,
        sa.ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    ),
    # "order" is a SQL keyword; SQLAlchemy quotes it automatically.
    sa.Column("order", sa.Integer, nullable=False),
    sa.Column("name", sa.String(255), nullable=False),
    # When True, the agent must present the step output to the user and get
    # explicit approval before calling finish_step.
    sa.Column("requires_approval", sa.Boolean, nullable=False, server_default="0"),
    sa.Column(
        "library_entry_id",
        sa.Integer,
        sa.ForeignKey("library_entries.id", ondelete="SET NULL"),
        nullable=True,
    ),
)

step_edges = sa.Table(
    "step_edges",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column(
        "workflow_id",
        sa.Integer,
        sa.ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "from_step_id",
        sa.Integer,
        sa.ForeignKey("steps.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "to_step_id",
        sa.Integer,
        sa.ForeignKey("steps.id", ondelete="CASCADE"),
        nullable=False,
    ),
    # null condition = unconditional / default edge
    sa.Column("condition", sa.JSON, nullable=True),
    # edges evaluated in ascending priority; first match wins
    sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
    # when True, this edge is part of a parallel fork (rendered side-by-side)
    sa.Column("parallel", sa.Boolean, nullable=False, server_default="0"),
)

playbooks = sa.Table(
    "playbooks",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column(
        "step_id",
        sa.Integer,
        sa.ForeignKey("steps.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    ),
    sa.Column("content", sa.Text, nullable=False),
)

library_entries = sa.Table(
    "library_entries",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("name", sa.String(255), nullable=False, unique=True),
    sa.Column("description", sa.Text),
    sa.Column("playbook", sa.Text, nullable=False),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
)

tasks = sa.Table(
    "tasks",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("workflow_id", sa.Integer, sa.ForeignKey("workflows.id"), nullable=False),
    sa.Column("name", sa.String(255), nullable=False),
    sa.Column("description", sa.Text),
    sa.Column("status", sa.String(32), nullable=False, server_default="todo"),
    # NULL when todo or done; set to the active step's id while in_progress
    sa.Column("current_step_id", sa.Integer, sa.ForeignKey("steps.id"), nullable=True),
    sa.Column("progress_notes", sa.Text),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
)

step_instances = sa.Table(
    "step_instances",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column(
        "task_id",
        sa.Integer,
        sa.ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "step_id",
        sa.Integer,
        sa.ForeignKey("steps.id"),
        nullable=True,
    ),
    sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
    sa.Column("input_data", sa.JSON),
    sa.Column("output", sa.JSON),
    sa.Column("completed_at", sa.DateTime),
)
