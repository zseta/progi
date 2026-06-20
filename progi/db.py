"""Shared database layer (SQLAlchemy Core + SQLite).

This module is the SINGLE source of truth for database access. Both the MCP
server and the web app import from here — neither writes raw SQL of its own.
That keeps behavior identical regardless of who initiates a change (the LLM via
an MCP tool, or a human via the web UI).

Domain
------
An AI-native project-management system. A **workflow** is a reusable template
made of **steps** connected by **edges**; each step carries a **playbook**
(markdown the AI agent follows). A **task** is created directly under a chosen workflow. The work loop advances
a task one step at a time by evaluating edge conditions on the submitted output
to choose the next step. All of the state-transition logic (start,
submit/advance, resolve inputs) lives here as plain functions so it is
implemented once, correctly — not re-derived by an LLM writing ad-hoc SQL.

Edges & branching
-----------------
Workflow steps form a directed graph. Each step can have zero or more outgoing
``step_edges``. A ``null`` condition on an edge means "unconditional / default".
When multiple conditional edges exist, they are evaluated in ascending
``priority`` order; the first matching edge wins. A step with no outgoing edges
is a terminal step — reaching it completes the task.

Concurrency
-----------
Two processes (MCP server and web server) may open the same SQLite file at the
same time. WAL mode + a busy timeout make concurrent reads/writes safe:
readers never block writers and a writer will wait briefly rather than failing
immediately with "database is locked". These pragmas are applied on every new
connection via the `connect` event listener below.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from .config import Config
from .models import library_entries, playbooks, step_edges, step_instances, steps, tasks, workflows
from .models import metadata  # noqa: F401 — re-exported for test helpers

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_engine: Engine | None = None


def _serialize_row(row: Any) -> dict[str, Any]:
    """Convert a SQLAlchemy mapping row to a plain dict, serializing datetimes to ISO strings."""
    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in dict(row).items()}


def _apply_sqlite_pragmas(dbapi_conn, _connection_record) -> None:
    """Set per-connection SQLite pragmas for safe concurrent access."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA busy_timeout=5000;")  # ms to wait on a locked DB
    cursor.execute("PRAGMA synchronous=NORMAL;")  # safe + fast with WAL
    cursor.close()


def get_engine(cfg: Config) -> Engine:
    """Return a process-wide singleton engine for the configured DB path."""
    global _engine
    if _engine is None:
        cfg.ensure_dirs()
        _engine = sa.create_engine(
            cfg.sqlalchemy_url,
            # check_same_thread=False lets the engine be shared across the
            # uvicorn worker thread and the main thread in bundled mode.
            connect_args={"check_same_thread": False},
        )
        event.listen(_engine, "connect", _apply_sqlite_pragmas)
    return _engine


def dispose_engine() -> None:
    """Dispose the engine (used on shutdown)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def init_db(cfg: Config) -> None:
    """Run all pending Alembic migrations.

    Call this once at startup before serving any requests. On a fresh install
    this creates all tables; on subsequent runs it applies only new migrations.
    """
    import pathlib

    from alembic import command
    from alembic.config import Config as AlembicConfig

    alembic_cfg = AlembicConfig()
    # Point at the alembic/ directory bundled inside the package.
    alembic_cfg.set_main_option("script_location", str(pathlib.Path(__file__).parent / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", cfg.sqlalchemy_url)
    cfg.ensure_dirs()
    command.upgrade(alembic_cfg, "head")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _ordered_steps(conn, workflow_id: int) -> list[dict[str, Any]]:
    """Return all steps for a workflow ordered by their display order."""
    rows = (
        conn.execute(
            sa.select(steps).where(steps.c.workflow_id == workflow_id).order_by(steps.c.order)
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def _start_step(conn, workflow_id: int) -> dict[str, Any]:
    """Return the entry-point step: the one with no forward-incoming edges.

    Back-edges (loop-backs from a higher-order step to a lower-order step) are
    excluded from the "incoming edge" check so that loop targets are not
    mistakenly disqualified from being the entry point.

    Falls back to the step with the lowest order if no edges exist yet
    (e.g. during initial creation before edges are inserted).
    """
    # Build order lookup for all steps in this workflow
    order_by_id = {
        r[0]: r[1]
        for r in conn.execute(
            sa.select(steps.c.id, steps.c.order).where(steps.c.workflow_id == workflow_id)
        ).fetchall()
    }
    if not order_by_id:
        raise ValueError(f"Workflow {workflow_id} has no steps.")

    # Step IDs that are targets of a *forward* edge (from lower-order → higher-order step).
    # Back-edges (loop returns) are excluded so they don't disqualify the entry step.
    target_ids = {
        to_id
        for to_id, from_id in conn.execute(
            sa.select(step_edges.c.to_step_id, step_edges.c.from_step_id)
            .where(step_edges.c.workflow_id == workflow_id)
        ).fetchall()
        if order_by_id.get(from_id, 0) < order_by_id.get(to_id, 0)
    }

    entry_candidates = [sid for sid in order_by_id if sid not in target_ids]
    if not entry_candidates:
        # Cycle or no edges — fall back to lowest order
        row = (
            conn.execute(
                sa.select(steps)
                .where(steps.c.workflow_id == workflow_id)
                .order_by(steps.c.order)
                .limit(1)
            )
            .mappings()
            .one()
        )
        return dict(row)

    # Among candidates pick the one with the lowest order
    row = (
        conn.execute(
            sa.select(steps)
            .where(steps.c.id.in_(entry_candidates))
            .order_by(steps.c.order)
            .limit(1)
        )
        .mappings()
        .one()
    )
    return dict(row)


def _evaluate_condition(condition: dict | None, output: dict) -> bool:
    """Return True if the edge condition matches the step output.

    A null condition always matches (unconditional / default edge).
    Supported operators: eq, neq, in, not_in.
    """
    if condition is None:
        return True
    field = condition["field"]
    value = output.get(field)
    op = condition["operator"]
    if op == "eq":
        return value == condition["value"]
    elif op == "neq":
        return value != condition["value"]
    elif op == "in":
        return value in condition["value"]
    elif op == "not_in":
        return value not in condition["value"]
    return False


def _resolve_next_step(conn, current_step_id: int, output: dict) -> dict[str, Any] | None:
    """Return the next step dict by evaluating outgoing edges, or None if terminal.

    Edges are evaluated in ascending priority order. The first edge whose
    condition matches the output is taken. Raises ValueError if edges exist but
    none match.
    """
    edges = (
        conn.execute(
            sa.select(step_edges)
            .where(step_edges.c.from_step_id == current_step_id)
            .order_by(step_edges.c.priority)
        )
        .mappings()
        .all()
    )

    if not edges:
        return None  # terminal step

    for edge in edges:
        if _evaluate_condition(edge["condition"], output):
            row = (
                conn.execute(sa.select(steps).where(steps.c.id == edge["to_step_id"]))
                .mappings()
                .one()
            )
            return dict(row)

    raise ValueError(
        f"No outgoing edge condition matched for step {current_step_id}. "
        f"Output fields: {list(output.keys())}. "
        f"Check that the output includes the field referenced by at least one edge condition, "
        f"or add an unconditional (null condition) fallback edge."
    )


# ---------------------------------------------------------------------------
# Workflow authoring
# ---------------------------------------------------------------------------


def save_workflow(
    cfg: Config,
    skeleton_json: dict[str, Any],
    playbooks_by_step: dict[str, str],
) -> dict[str, Any]:
    """Persist a workflow, its steps, edges, and playbooks in one transaction.

    skeleton_json shape::

        {
            "name": str,
            "description": str,
            "process": [
                {"order": int, "name": str, "input_spec": {...}, "output_spec": {...}}
            ],
            "edges": [                          # optional; auto-generated if absent
                {"from": str, "to": str, "condition": {...} | null, "priority": int}
            ]
        }

    If ``edges`` is absent, linear edges are auto-generated from the step
    ``order`` values (step[i] → step[i+1]).

    playbooks_by_step: mapping of step name → playbook markdown string.
    """
    engine = get_engine(cfg)
    with engine.begin() as conn:
        wf_id = conn.execute(
            sa.insert(workflows).values(
                name=skeleton_json["name"],
                description=skeleton_json.get("description"),
            )
        ).inserted_primary_key[0]

        step_rows: list[dict[str, Any]] = []
        for step in sorted(skeleton_json["process"], key=lambda s: s["order"]):
            step_id = conn.execute(
                sa.insert(steps).values(
                    workflow_id=wf_id,
                    order=step["order"],
                    name=step["name"],
                    input_spec=step["input_spec"],
                    output_spec=step["output_spec"],
                    requires_approval=step.get("requires_approval", False),
                )
            ).inserted_primary_key[0]
            step_row = conn.execute(sa.select(steps).where(steps.c.id == step_id)).mappings().one()
            step_rows.append(dict(step_row))

        # Build name → id lookup for edge resolution
        step_id_by_name = {s["name"]: s["id"] for s in step_rows}

        # Insert edges
        edge_defs = skeleton_json.get("edges")
        if edge_defs:
            for edge in edge_defs:
                from_id = step_id_by_name[edge["from"]]
                to_id = step_id_by_name[edge["to"]]
                conn.execute(
                    sa.insert(step_edges).values(
                        workflow_id=wf_id,
                        from_step_id=from_id,
                        to_step_id=to_id,
                        condition=edge.get("condition"),
                        priority=edge.get("priority", 0),
                    )
                )
        else:
            # Auto-generate linear edges from order
            for i in range(len(step_rows) - 1):
                conn.execute(
                    sa.insert(step_edges).values(
                        workflow_id=wf_id,
                        from_step_id=step_rows[i]["id"],
                        to_step_id=step_rows[i + 1]["id"],
                        condition=None,
                        priority=0,
                    )
                )

        for step_row in step_rows:
            playbook_content = playbooks_by_step.get(step_row["name"])
            if playbook_content:
                conn.execute(
                    sa.insert(playbooks).values(step_id=step_row["id"], content=playbook_content)
                )

        workflow = (
            conn.execute(sa.select(workflows).where(workflows.c.id == wf_id)).mappings().one()
        )

    result = dict(workflow)
    result["steps"] = step_rows
    return result


def list_workflows(cfg: Config) -> list[dict[str, Any]]:
    """Return all workflows with their ordered steps."""
    engine = get_engine(cfg)
    with engine.connect() as conn:
        wf_rows = conn.execute(sa.select(workflows).order_by(workflows.c.id)).mappings().all()
        step_rows = (
            conn.execute(sa.select(steps).order_by(steps.c.workflow_id, steps.c.order))
            .mappings()
            .all()
        )

    steps_by_workflow: dict[int, list[dict[str, Any]]] = {}
    for s in step_rows:
        steps_by_workflow.setdefault(s["workflow_id"], []).append(
            {
                "id": s["id"],
                "order": s["order"],
                "name": s["name"],
                "input_spec": s["input_spec"],
                "output_spec": s["output_spec"],
            }
        )

    return [
        {
            "id": wf["id"],
            "name": wf["name"],
            "description": wf["description"],
            "steps": steps_by_workflow.get(wf["id"], []),
        }
        for wf in wf_rows
    ]


def get_playbook_authoring_context(cfg: Config, step_id: int) -> dict[str, Any]:
    """Return the workflow + sibling context needed to author a step's playbook."""
    engine = get_engine(cfg)
    with engine.connect() as conn:
        step = conn.execute(sa.select(steps).where(steps.c.id == step_id)).mappings().one_or_none()
        if step is None:
            raise ValueError(f"Step {step_id} not found.")

        wf = (
            conn.execute(sa.select(workflows).where(workflows.c.id == step["workflow_id"]))
            .mappings()
            .one()
        )

        siblings = (
            conn.execute(
                sa.select(steps.c.name, steps.c.order)
                .where(steps.c.workflow_id == step["workflow_id"])
                .order_by(steps.c.order)
            )
            .mappings()
            .all()
        )

    return {
        "workflow": dict(wf),
        "step": dict(step),
        "siblings": [dict(s) for s in siblings],
    }


def delete_workflow(cfg: Config, workflow_id: int) -> None:
    """Delete a workflow and all its dependent data."""
    engine = get_engine(cfg)
    with engine.begin() as conn:
        # tasks.workflow_id has no CASCADE, so delete tasks (and their
        # step_instances via cascade) before touching the workflow.
        task_ids = (
            conn.execute(sa.select(tasks.c.id).where(tasks.c.workflow_id == workflow_id))
            .scalars()
            .all()
        )
        if task_ids:
            conn.execute(sa.delete(step_instances).where(step_instances.c.task_id.in_(task_ids)))
            conn.execute(sa.delete(tasks).where(tasks.c.id.in_(task_ids)))
        result = conn.execute(sa.delete(workflows).where(workflows.c.id == workflow_id))
        if result.rowcount == 0:
            raise ValueError(f"Workflow {workflow_id} not found.")


def update_workflow(cfg: Config, workflow_id: int, name: str) -> dict[str, Any]:
    """Rename a workflow and return the updated record."""
    engine = get_engine(cfg)
    with engine.begin() as conn:
        result = conn.execute(
            sa.update(workflows).where(workflows.c.id == workflow_id).values(name=name)
        )
        if result.rowcount == 0:
            raise ValueError(f"Workflow {workflow_id} not found.")
        row = (
            conn.execute(sa.select(workflows).where(workflows.c.id == workflow_id)).mappings().one()
        )
    return dict(row)


def update_step(
    cfg: Config,
    step_id: int,
    *,
    name: str | None = None,
    input_spec: dict[str, Any] | None = None,
    output_spec: dict[str, Any] | None = None,
    order: int | None = None,
    requires_approval: bool | None = None,
) -> dict[str, Any]:
    """Update one or more fields of a step; only non-None fields change."""
    values: dict[str, Any] = {}
    if name is not None:
        values["name"] = name
    if input_spec is not None:
        values["input_spec"] = input_spec
    if output_spec is not None:
        values["output_spec"] = output_spec
    if order is not None:
        values["order"] = order
    if requires_approval is not None:
        values["requires_approval"] = requires_approval

    engine = get_engine(cfg)
    with engine.begin() as conn:
        existing = conn.execute(sa.select(steps.c.id).where(steps.c.id == step_id)).first()
        if existing is None:
            raise ValueError(f"Step {step_id} not found.")
        if values:
            conn.execute(sa.update(steps).where(steps.c.id == step_id).values(**values))
        row = conn.execute(sa.select(steps).where(steps.c.id == step_id)).mappings().one()
    return dict(row)


def update_playbook(cfg: Config, step_id: int, content: str) -> dict[str, Any]:
    """Upsert the playbook content for a step (insert if none exists)."""
    engine = get_engine(cfg)
    with engine.begin() as conn:
        result = conn.execute(
            sa.update(playbooks).where(playbooks.c.step_id == step_id).values(content=content)
        )
        if result.rowcount == 0:
            conn.execute(sa.insert(playbooks).values(step_id=step_id, content=content))
        row = (
            conn.execute(sa.select(playbooks).where(playbooks.c.step_id == step_id))
            .mappings()
            .one()
        )
    return dict(row)


# ---------------------------------------------------------------------------
# Task creation & the work loop
# ---------------------------------------------------------------------------


def create_task(cfg: Config, name: str, workflow_id: int, description: str = "") -> dict[str, Any]:
    """Create a task directly under a workflow.

    Does NOT start the task (status stays 'todo', current_step_id stays NULL).
    Step instances are created lazily as steps are activated — this avoids
    phantom instances for branches that are never taken.

    Returns the task with a ``first_step`` preview.
    """
    engine = get_engine(cfg)
    with engine.begin() as conn:
        step_rows = _ordered_steps(conn, workflow_id)
        if not step_rows:
            raise ValueError(f"Workflow {workflow_id} has no steps.")

        task_id = conn.execute(
            sa.insert(tasks).values(
                workflow_id=workflow_id,
                name=name,
                description=description or None,
                status="todo",
                current_step_id=None,
            )
        ).inserted_primary_key[0]

        task = conn.execute(sa.select(tasks).where(tasks.c.id == task_id)).mappings().one()

    result = dict(task)
    first = _start_step_from_rows(step_rows)
    result["first_step"] = {
        "name": first["name"],
        "order": first["order"],
        "input_spec": first["input_spec"],
    }
    return result


def _start_step_from_rows(step_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the first step (by order) from an already-fetched list."""
    return min(step_rows, key=lambda s: s["order"])


def _activate_step(
    conn,
    task_id: int,
    task_workflow_id: int,
    step: dict[str, Any],
    input_data: dict[str, Any],
) -> None:
    """Create a step_instance for ``step`` and mark it active."""
    conn.execute(
        sa.insert(step_instances).values(
            task_id=task_id,
            step_id=step["id"],
            status="active",
            input_data=input_data,
        )
    )
    conn.execute(
        sa.update(tasks)
        .where(tasks.c.id == task_id)
        .values(current_step_id=step["id"], status="in_progress")
    )


def start_task(cfg: Config, task_id: int) -> dict[str, Any]:
    """First pick-up only (status must be 'todo').

    Finds the entry-point step (no incoming edges), creates its step_instance,
    resolves input_data from the static input_spec, and sets the task to
    'in_progress'.
    """
    engine = get_engine(cfg)
    with engine.begin() as conn:
        task = conn.execute(sa.select(tasks).where(tasks.c.id == task_id)).mappings().one_or_none()
        if task is None:
            raise ValueError(f"Task {task_id} not found.")
        if task["status"] != "todo":
            raise ValueError(
                f"start_task can only be called on a 'todo' task "
                f"(task {task_id} is '{task['status']}')."
            )

        first_step = _start_step(conn, task["workflow_id"])
        input_spec = first_step["input_spec"]
        input_data = {
            "description": input_spec["description"],
            "source": "static",
        }

        _activate_step(conn, task_id, task["workflow_id"], first_step, input_data)

        updated = conn.execute(sa.select(tasks).where(tasks.c.id == task_id)).mappings().one()
    return dict(updated)


def list_tasks(cfg: Config, status: str = "", workflow_id: int = 0) -> list[dict[str, Any]]:
    """Return a summary list of tasks, optionally filtered by status / workflow."""
    engine = get_engine(cfg)
    sd_alias = steps.alias("sd")
    query = (
        sa.select(
            tasks.c.id,
            tasks.c.name,
            workflows.c.name.label("workflow_name"),
            tasks.c.status,
            tasks.c.current_step_id,
            tasks.c.progress_notes,
            sd_alias.c.name.label("current_step_name"),
        )
        .select_from(
            tasks.join(workflows, workflows.c.id == tasks.c.workflow_id).outerjoin(
                sd_alias,
                sd_alias.c.id == tasks.c.current_step_id,
            )
        )
        .order_by(tasks.c.created_at, tasks.c.id)
    )
    if status:
        query = query.where(tasks.c.status == status)
    if workflow_id:
        query = query.where(tasks.c.workflow_id == workflow_id)

    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()
    return [dict(r) for r in rows]


def start_or_continue_task(cfg: Config, task_id: int) -> dict[str, Any]:
    """Main work-loop entry point.

    - done        → returns a done message.
    - todo        → starts the task (todo → in_progress), returns full step context.
    - in_progress → returns full step context so the agent can resume.

    Full context: task info, current step name + position, input_data, output_spec,
    playbook content, and progress_notes (if any).
    """
    engine = get_engine(cfg)
    with engine.connect() as conn:
        task = conn.execute(sa.select(tasks).where(tasks.c.id == task_id)).mappings().one_or_none()
        if task is None:
            raise ValueError(f"Task {task_id} not found.")
        if task["status"] == "done":
            return {
                "status": "done",
                "message": f"Task '{task['name']}' is already complete.",
            }

    if task["status"] == "todo":
        task = start_task(cfg, task_id)

    with engine.connect() as conn:
        current_step = (
            conn.execute(sa.select(steps).where(steps.c.id == task["current_step_id"]))
            .mappings()
            .one()
        )

        si = (
            conn.execute(
                sa.select(step_instances).where(
                    step_instances.c.task_id == task_id,
                    step_instances.c.step_id == current_step["id"],
                    step_instances.c.status == "active",
                )
            )
            .mappings()
            .one_or_none()
        )

        pb = conn.execute(
            sa.select(playbooks.c.content).where(playbooks.c.step_id == current_step["id"])
        ).first()

    result: dict[str, Any] = {
        "task": {
            "id": task["id"],
            "name": task["name"],
            "status": task["status"],
            "description": task["description"],
        },
        "current_step": {
            "name": current_step["name"],
            "input_data": si["input_data"] if si else None,
            "output_spec": current_step["output_spec"],
            "playbook": pb[0] if pb else None,
            "requires_approval": bool(current_step["requires_approval"]),
        },
    }
    if task.get("progress_notes"):
        result["progress_notes"] = task["progress_notes"]
    return result


def update_progress_notes(cfg: Config, task_id: int, notes: str) -> dict[str, Any]:
    """Overwrite progress_notes on the task and return the updated task."""
    engine = get_engine(cfg)
    with engine.begin() as conn:
        result = conn.execute(
            sa.update(tasks).where(tasks.c.id == task_id).values(progress_notes=notes)
        )
        if result.rowcount == 0:
            raise ValueError(f"Task {task_id} not found.")
        row = conn.execute(sa.select(tasks).where(tasks.c.id == task_id)).mappings().one()
    return dict(row)


def submit_output(
    cfg: Config, task_id: int, output: dict[str, Any], task_name: str | None = None
) -> dict[str, Any]:
    """Complete the current step, evaluate edge conditions, then advance or finish.

    Marks the active step instance complete (stores output + completed_at),
    clears progress_notes, then either activates the next step (resolving
    input_data) or sets the task to 'done'. One transaction.

    If ``task_name`` is provided, the task is renamed in the same transaction —
    useful when the agent learns a better name from the step's output.

    Returns next-step info or {'status': 'done'}.
    """
    engine = get_engine(cfg)
    with engine.begin() as conn:
        task = conn.execute(sa.select(tasks).where(tasks.c.id == task_id)).mappings().one_or_none()
        if task is None:
            raise ValueError(f"Task {task_id} not found.")
        if task["status"] == "done":
            raise ValueError(f"Task {task_id} is already done.")
        if task["status"] == "todo":
            raise ValueError(f"Task {task_id} has not been started yet.")

        current_step = (
            conn.execute(sa.select(steps).where(steps.c.id == task["current_step_id"]))
            .mappings()
            .one()
        )

        current_si = (
            conn.execute(
                sa.select(step_instances).where(
                    step_instances.c.task_id == task_id,
                    step_instances.c.step_id == current_step["id"],
                    step_instances.c.status == "active",
                )
            )
            .mappings()
            .one_or_none()
        )
        if current_si is None:
            raise ValueError(
                f"No active step instance found for task {task_id} "
                f"at step '{current_step['name']}'."
            )

        # Mark current step complete
        conn.execute(
            sa.update(step_instances)
            .where(step_instances.c.id == current_si["id"])
            .values(status="complete", output=output, completed_at=_now())
        )

        # Optionally rename the task now that the agent has more context
        if task_name:
            conn.execute(sa.update(tasks).where(tasks.c.id == task_id).values(name=task_name))

        # Resolve next step via edge conditions
        next_step = _resolve_next_step(conn, current_step["id"], output)

        if next_step is None:
            # Terminal step — task is done
            conn.execute(
                sa.update(tasks)
                .where(tasks.c.id == task_id)
                .values(status="done", current_step_id=None, progress_notes=None)
            )
            return {"status": "done"}

        # Resolve input_data for next step
        next_input_spec = next_step["input_spec"]
        if next_input_spec.get("source") == "previous_step_output":
            from_step_name = next_input_spec.get("from_step")
            if from_step_name and from_step_name != current_step["name"]:
                # Pull output from a specific earlier step by name
                source_step_row = conn.execute(
                    sa.select(steps.c.id).where(
                        steps.c.workflow_id == task["workflow_id"],
                        steps.c.name == from_step_name,
                    )
                ).first()
                if source_step_row is None:
                    raise ValueError(f"from_step '{from_step_name}' not found in workflow.")
                source_si = conn.execute(
                    sa.select(step_instances.c.output).where(
                        step_instances.c.task_id == task_id,
                        step_instances.c.step_id == source_step_row[0],
                        step_instances.c.status == "complete",
                    ).order_by(step_instances.c.id.desc())
                ).first()
                source_output = source_si[0] if source_si else {}
            else:
                # Default: use the step we just completed
                source_output = output

            next_input_data = {
                "value": source_output.get("value", source_output),
                "from_step": from_step_name or current_step["name"],
            }
        else:
            next_input_data = {
                "description": next_input_spec.get("description", ""),
                "source": "static",
            }

        # Activate next step (create instance + update task pointer)
        conn.execute(
            sa.insert(step_instances).values(
                task_id=task_id,
                step_id=next_step["id"],
                status="active",
                input_data=next_input_data,
            )
        )
        conn.execute(
            sa.update(tasks)
            .where(tasks.c.id == task_id)
            .values(current_step_id=next_step["id"], progress_notes=None)
        )

        pb = conn.execute(
            sa.select(playbooks.c.content).where(playbooks.c.step_id == next_step["id"])
        ).first()

    return {
        "status": "in_progress",
        "next_step": {
            "name": next_step["name"],
            "input_data": next_input_data,
            "playbook": pb[0] if pb else None,
        },
    }


# ---------------------------------------------------------------------------
# Read helpers for the web dashboard
# ---------------------------------------------------------------------------


def get_workflow_with_playbooks(cfg: Config, workflow_id: int) -> dict[str, Any]:
    """Return a single workflow with its steps, edges, and playbook content."""
    engine = get_engine(cfg)
    with engine.connect() as conn:
        wf = (
            conn.execute(sa.select(workflows).where(workflows.c.id == workflow_id))
            .mappings()
            .one_or_none()
        )
        if wf is None:
            raise ValueError(f"Workflow {workflow_id} not found.")

        step_rows = (
            conn.execute(
                sa.select(steps).where(steps.c.workflow_id == workflow_id).order_by(steps.c.order)
            )
            .mappings()
            .all()
        )

        step_ids = [s["id"] for s in step_rows]
        pb_rows = (
            conn.execute(sa.select(playbooks).where(playbooks.c.step_id.in_(step_ids)))
            .mappings()
            .all()
            if step_ids
            else []
        )

        edge_rows = (
            conn.execute(
                sa.select(step_edges)
                .where(step_edges.c.workflow_id == workflow_id)
                .order_by(step_edges.c.from_step_id, step_edges.c.priority)
            )
            .mappings()
            .all()
            if step_ids
            else []
        )

    playbook_by_step = {pb["step_id"]: pb["content"] for pb in pb_rows}

    return {
        "id": wf["id"],
        "name": wf["name"],
        "description": wf["description"],
        "steps": [
            {
                "id": s["id"],
                "order": s["order"],
                "name": s["name"],
                "input_spec": s["input_spec"],
                "output_spec": s["output_spec"],
                "playbook": playbook_by_step.get(s["id"]),
            }
            for s in step_rows
        ],
        "edges": [
            {
                "from_step_id": e["from_step_id"],
                "to_step_id": e["to_step_id"],
                "condition": e["condition"],
                "priority": e["priority"],
            }
            for e in edge_rows
        ],
    }


def get_step_detail(cfg: Config, workflow_id: int, step_id: int) -> dict[str, Any]:
    """Return a single step with its playbook, and derived prev/next steps."""
    engine = get_engine(cfg)
    with engine.connect() as conn:
        wf = (
            conn.execute(
                sa.select(workflows.c.id, workflows.c.name).where(workflows.c.id == workflow_id)
            )
            .mappings()
            .one_or_none()
        )
        if wf is None:
            raise ValueError(f"Workflow {workflow_id} not found.")

        step = (
            conn.execute(
                sa.select(steps).where(
                    steps.c.id == step_id,
                    steps.c.workflow_id == workflow_id,
                )
            )
            .mappings()
            .one_or_none()
        )
        if step is None:
            raise ValueError(f"Step {step_id} not found in workflow {workflow_id}.")

        pb = conn.execute(
            sa.select(playbooks.c.content).where(playbooks.c.step_id == step_id)
        ).scalar()

        edge_rows = (
            conn.execute(sa.select(step_edges).where(step_edges.c.workflow_id == workflow_id))
            .mappings()
            .all()
        )

        # Collect neighbour step IDs
        prev_ids = {e["from_step_id"] for e in edge_rows if e["to_step_id"] == step_id}
        next_ids = {e["to_step_id"] for e in edge_rows if e["from_step_id"] == step_id}
        neighbour_ids = prev_ids | next_ids

        step_names: dict[int, str] = {}
        if neighbour_ids:
            name_rows = (
                conn.execute(
                    sa.select(steps.c.id, steps.c.name).where(steps.c.id.in_(neighbour_ids))
                )
                .mappings()
                .all()
            )
            step_names = {r["id"]: r["name"] for r in name_rows}

    # Build prev/next with conditions
    prev_steps = [
        {
            "id": e["from_step_id"],
            "name": step_names.get(e["from_step_id"], str(e["from_step_id"])),
            "condition": e["condition"],
        }
        for e in edge_rows
        if e["to_step_id"] == step_id
    ]
    next_steps = [
        {
            "id": e["to_step_id"],
            "name": step_names.get(e["to_step_id"], str(e["to_step_id"])),
            "condition": e["condition"],
        }
        for e in edge_rows
        if e["from_step_id"] == step_id
    ]

    return {
        "workflow": {"id": wf["id"], "name": wf["name"]},
        "step": {
            "id": step["id"],
            "order": step["order"],
            "name": step["name"],
            "input_spec": step["input_spec"],
            "output_spec": step["output_spec"],
            "playbook": pb,
            "library_entry_id": step["library_entry_id"],
        },
        "prev_steps": prev_steps,
        "next_steps": next_steps,
    }


def get_task_detail(cfg: Config, task_id: int) -> dict[str, Any]:
    """Return a task with its full step-instance history for the task detail modal."""
    engine = get_engine(cfg)
    with engine.connect() as conn:
        row = (
            conn.execute(
                sa.select(
                    tasks.c.id,
                    tasks.c.name,
                    tasks.c.description,
                    tasks.c.status,
                    tasks.c.current_step_id,
                    tasks.c.progress_notes,
                    tasks.c.created_at,
                    workflows.c.id.label("workflow_id"),
                    workflows.c.name.label("workflow_name"),
                )
                .select_from(tasks.join(workflows, workflows.c.id == tasks.c.workflow_id))
                .where(tasks.c.id == task_id)
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ValueError(f"Task {task_id} not found.")

        task = dict(row)

        # Current step name (if in_progress)
        current_step_name: str | None = None
        if task["current_step_id"]:
            current_step_name = conn.execute(
                sa.select(steps.c.name).where(steps.c.id == task["current_step_id"])
            ).scalar()

        # Step-instance history (most recent first via id desc)
        si_rows = (
            conn.execute(
                sa.select(
                    step_instances.c.id,
                    step_instances.c.step_id,
                    step_instances.c.status,
                    step_instances.c.input_data,
                    step_instances.c.output,
                    step_instances.c.completed_at,
                    steps.c.name.label("step_name"),
                )
                .select_from(step_instances.join(steps, steps.c.id == step_instances.c.step_id))
                .where(step_instances.c.task_id == task_id)
                .order_by(
                    # Active instance floats to top, then newest first
                    sa.case((step_instances.c.status == "active", 0), else_=1),
                    step_instances.c.id.desc(),
                )
            )
            .mappings()
            .all()
        )

    return {
        "task": {
            "id": task["id"],
            "name": task["name"],
            "description": task["description"],
            "status": task["status"],
            "progress_notes": task["progress_notes"],
            "created_at": task["created_at"].isoformat() if task["created_at"] else None,
            "workflow_id": task["workflow_id"],
            "workflow_name": task["workflow_name"],
            "current_step_id": task["current_step_id"],
            "current_step_name": current_step_name,
        },
        "step_instances": [
            {
                "id": si["id"],
                "step_id": si["step_id"],
                "step_name": si["step_name"],
                "status": si["status"],
                "input_data": si["input_data"],
                "output": si["output"],
                "completed_at": si["completed_at"].isoformat() if si["completed_at"] else None,
            }
            for si in si_rows
        ],
    }


def board_tasks(cfg: Config, q: str = "", workflow_id: int | None = None) -> list[dict[str, Any]]:
    """Return all tasks ordered by most recent activity for the board list view."""
    engine = get_engine(cfg)
    sd_alias = steps.alias("sd")

    si_alias = step_instances.alias("si_latest")
    latest_activity = (
        sa.select(
            si_alias.c.task_id,
            sa.func.max(si_alias.c.completed_at).label("last_active"),
        )
        .group_by(si_alias.c.task_id)
        .subquery()
    )

    query = (
        sa.select(
            tasks.c.id,
            tasks.c.name,
            workflows.c.name.label("workflow_name"),
            tasks.c.status,
            tasks.c.current_step_id,
            tasks.c.progress_notes,
            sd_alias.c.name.label("current_step_name"),
            tasks.c.created_at,
            latest_activity.c.last_active,
        )
        .select_from(
            tasks.join(workflows, workflows.c.id == tasks.c.workflow_id)
            .outerjoin(sd_alias, sd_alias.c.id == tasks.c.current_step_id)
            .outerjoin(latest_activity, latest_activity.c.task_id == tasks.c.id)
        )
        .order_by(
            sa.func.coalesce(latest_activity.c.last_active, tasks.c.created_at).desc()
        )
    )

    if q:
        pattern = f"%{q}%"
        query = query.where(
            sa.or_(
                tasks.c.name.ilike(pattern),
                workflows.c.name.ilike(pattern),
                sd_alias.c.name.ilike(pattern),
            )
        )

    if workflow_id is not None:
        query = query.where(tasks.c.workflow_id == workflow_id)

    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------


def list_library_entries(cfg: Config) -> list[dict[str, Any]]:
    """Return all library entries ordered by name."""
    engine = get_engine(cfg)
    with engine.connect() as conn:
        rows = (
            conn.execute(sa.select(library_entries).order_by(library_entries.c.name))
            .mappings()
            .all()
        )
    return [_serialize_row(r) for r in rows]


def get_library_entry(cfg: Config, entry_id: int) -> dict[str, Any]:
    """Return a single library entry; raises ValueError if not found."""
    engine = get_engine(cfg)
    with engine.connect() as conn:
        row = (
            conn.execute(
                sa.select(library_entries).where(library_entries.c.id == entry_id)
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise ValueError(f"Library entry {entry_id} not found.")
    return _serialize_row(row)


def create_library_entry(
    cfg: Config, name: str, description: str, playbook: str
) -> dict[str, Any]:
    """Create a new library entry and return it."""
    engine = get_engine(cfg)
    try:
        with engine.begin() as conn:
            entry_id = conn.execute(
                sa.insert(library_entries).values(
                    name=name,
                    description=description or None,
                    playbook=playbook,
                )
            ).inserted_primary_key[0]
            row = (
                conn.execute(
                    sa.select(library_entries).where(library_entries.c.id == entry_id)
                )
                .mappings()
                .one()
            )
    except IntegrityError:
        raise ValueError(f"A library entry named '{name}' already exists.")
    return _serialize_row(row)


def update_library_entry(
    cfg: Config,
    entry_id: int,
    *,
    name: str | None = None,
    description: str | None = None,
    playbook: str | None = None,
) -> dict[str, Any]:
    """Update a library entry (only non-None fields are changed)."""
    engine = get_engine(cfg)
    values: dict[str, Any] = {}
    if name is not None:
        values["name"] = name
    if description is not None:
        values["description"] = description
    if playbook is not None:
        values["playbook"] = playbook
    if not values:
        return get_library_entry(cfg, entry_id)
    try:
        with engine.begin() as conn:
            result = conn.execute(
                sa.update(library_entries)
                .where(library_entries.c.id == entry_id)
                .values(**values)
            )
            if result.rowcount == 0:
                raise ValueError(f"Library entry {entry_id} not found.")
            row = (
                conn.execute(
                    sa.select(library_entries).where(library_entries.c.id == entry_id)
                )
                .mappings()
                .one()
            )
    except IntegrityError:
        raise ValueError(f"A library entry named '{values['name']}' already exists.")
    return _serialize_row(row)


def delete_library_entry(cfg: Config, entry_id: int) -> None:
    """Delete a library entry; steps referencing it will have library_entry_id set to NULL."""
    engine = get_engine(cfg)
    with engine.begin() as conn:
        conn.execute(
            sa.delete(library_entries).where(library_entries.c.id == entry_id)
        )


def create_library_entry_from_step(
    cfg: Config, step_id: int, name: str, description: str
) -> dict[str, Any]:
    """Create a library entry from an existing step's playbook and link it back."""
    engine = get_engine(cfg)
    try:
        with engine.begin() as conn:
            pb_content = conn.execute(
                sa.select(playbooks.c.content).where(playbooks.c.step_id == step_id)
            ).scalar()
            if pb_content is None:
                pb_content = ""
            entry_id = conn.execute(
                sa.insert(library_entries).values(
                    name=name,
                    description=description or None,
                    playbook=pb_content,
                )
            ).inserted_primary_key[0]
            conn.execute(
                sa.update(steps)
                .where(steps.c.id == step_id)
                .values(library_entry_id=entry_id)
            )
            row = (
                conn.execute(
                    sa.select(library_entries).where(library_entries.c.id == entry_id)
                )
                .mappings()
                .one()
            )
    except IntegrityError:
        raise ValueError(f"A library entry named '{name}' already exists.")
    return _serialize_row(row)


def get_library_entry_workflows(cfg: Config, entry_id: int) -> list[dict[str, Any]]:
    """Return all workflows/steps that link to the given library entry."""
    engine = get_engine(cfg)
    with engine.connect() as conn:
        rows = (
            conn.execute(
                sa.select(
                    steps.c.id.label("step_id"),
                    steps.c.name.label("step_name"),
                    workflows.c.id.label("workflow_id"),
                    workflows.c.name.label("workflow_name"),
                )
                .select_from(steps.join(workflows, workflows.c.id == steps.c.workflow_id))
                .where(steps.c.library_entry_id == entry_id)
                .order_by(workflows.c.name, steps.c.order)
            )
            .mappings()
            .all()
        )
    return [dict(r) for r in rows]


def get_library_entries_summary(cfg: Config) -> list[dict[str, Any]]:
    """Return [{name, description}] for all library entries — for MCP prompt injection."""
    engine = get_engine(cfg)
    with engine.connect() as conn:
        rows = (
            conn.execute(
                sa.select(library_entries.c.name, library_entries.c.description).order_by(
                    library_entries.c.name
                )
            )
            .mappings()
            .all()
        )
    return [dict(r) for r in rows]
