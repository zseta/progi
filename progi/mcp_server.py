"""MCP server (FastMCP).

Exposes the AI-native project-management system as MCP tools over stdio. Each tool
is a thin wrapper that delegates to `progi.db` — no business logic or SQL lives
here. Two tool families:

- **Work loop**: create_task, list_tasks,
  start_or_continue_task, update_progress_notes, submit_output.
- **Workflow authoring**: get_process_skeleton_prompt,
  get_playbook_authoring_prompt, save_workflow, list_workflows,
  update_playbook.

IMPORTANT (stdio hygiene): when running over stdio, stdout is the MCP protocol
channel. Never `print()` to stdout. Use logging configured to stderr (see
`logging_setup`).
"""

from __future__ import annotations

import json
from pathlib import Path

from fastmcp import FastMCP

from . import db
from .config import Config, load_config
from .logging_setup import configure_logging

mcp: FastMCP = FastMCP("progi")

# Config is loaded once at import time; the CLI may also pass an explicit Config
# to `run()` for the bundled mode.
_cfg: Config = load_config()


def _monitoring_url(path: str = "") -> str:
    """Return the full URL to the monitoring web app, optionally with a path."""
    base = f"http://{_cfg.web_host}:{_cfg.web_port}"
    return base + path if path else base


_PROMPTS_DIR = Path(__file__).parent / "prompts"
_WORKFLOW_SKELETON_MD = _PROMPTS_DIR / "workflow_skeleton.md"
_PLAYBOOK_MD = _PROMPTS_DIR / "playbook.md"


# ---------------------------------------------------------------------------
# Work-loop tools
# ---------------------------------------------------------------------------


@mcp.tool(title="Create Task")
def create_task(name: str, workflow_id: int, description: str = "") -> dict:
    """Create a new task under the given workflow.

    Creates the task (status 'todo') and returns the task plus a preview of its
    first step. Before calling this, confirm the workflow choice with the user
    AND ask them what they want to name the task.
    """
    result = db.create_task(_cfg, name, workflow_id, description)
    result["monitoring_url"] = _monitoring_url(f"/tasks/{result['id']}")
    return result


@mcp.tool(title="List Tasks")
def list_tasks(status: str = "", workflow_id: int = 0) -> dict:
    """List tasks, optionally filtered by status and/or workflow_id.

    Empty string / 0 means no filter. "My todos" = status="todo".
    """
    return {"tasks": db.list_tasks(_cfg, status, workflow_id), "monitoring_url": _monitoring_url("/")}


@mcp.tool(title="Start or Continue Task")
def start_or_continue_task(task_id: int) -> dict:
    """Main work-loop entry point.

    - done        → returns a done message.
    - todo        → starts the task (todo → in_progress) and returns step context.
    - in_progress → returns step context so the agent can resume.

    Context includes task info, the current step name + position, input_data,
    output_spec (the expected format/type of the deliverable), the playbook
    markdown, and progress_notes (if any).

    Before calling submit_output, verify that your output satisfies output_spec
    (correct type, meets constraints, includes any fields referenced by branching
    conditions).
    """
    result = db.start_or_continue_task(_cfg, task_id)
    result["monitoring_url"] = _monitoring_url(f"/tasks/{task_id}")
    return result


@mcp.tool(title="Update Progress Notes")
def update_progress_notes(task_id: int, notes: str) -> dict:
    """Overwrite a task's progress_notes.

    Only call this when the user explicitly asks to save or update progress notes.
    Notes are cleared automatically when a step completes.
    """
    return db.update_progress_notes(_cfg, task_id, notes)


@mcp.tool(title="Submit Output")
def submit_output(task_id: int, output: dict, task_name: str = "") -> dict:
    """Mark the current step complete, store its output, and advance.

    Either returns the next step's info (name + playbook, so the agent can
    continue immediately) or {'status': 'done'} if it was the last step.

    Pass task_name to rename the task when you now have enough context to give
    it a meaningful name (e.g. after the first step reveals what the task is
    actually about). Leave it empty to keep the current name.

    IMPORTANT — approval gate: if start_or_continue_task returned
    current_step.requires_approval = true for this step, you MUST present the
    output to the user and ask for explicit approval BEFORE calling this tool.
    Only call submit_output once the user has confirmed they are happy with the
    output. If they request changes, make them first, then ask again.
    """
    return db.submit_output(_cfg, task_id, output, task_name or None)


# ---------------------------------------------------------------------------
# Workflow authoring tools
# ---------------------------------------------------------------------------


@mcp.tool(title="Get Process Skeleton Prompt")
def get_process_skeleton_prompt() -> str:
    """Return the Pass 1 system prompt for authoring a new workflow's skeleton.

    The harness uses it to help the user convert a plain-language workflow
    description into a structured process skeleton (steps with input/output specs,
    no playbooks yet).
    """
    return _WORKFLOW_SKELETON_MD.read_text(encoding="utf-8")


@mcp.tool(title="Get Playbook Authoring Prompt")
def get_playbook_authoring_prompt(step_id: int) -> str:
    """Return the Pass 2 system prompt for authoring a step's playbook.

    Workflow context (the full process, this step's position, and its
    input/output specs) is injected at the top of the prompt template.
    """
    ctx = db.get_playbook_authoring_context(_cfg, step_id)
    wf = ctx["workflow"]
    step = ctx["step"]
    siblings = ctx["siblings"]

    process_list = " → ".join(
        f"**{s['name']}**" if s["name"] == step["name"] else s["name"]
        for s in siblings
    )

    requires_approval = bool(step.get("requires_approval", False))
    approval_status = "YES — agent must show output to user and get approval before submitting" if requires_approval else "NO — agent may submit immediately"

    context_block = f"""<!-- CONTEXT INJECTED BY MCP SERVER -->
## Workflow Context

- **Workflow**: {wf['name']} — {wf['description']}
- **Full process**: {process_list}
- **This step**: **{step['name']}**
  - input_spec: {json.dumps(step['input_spec'], indent=2)}
  - output_spec: {json.dumps(step['output_spec'], indent=2)}
  - requires_approval (current value): **{approval_status}**

---

"""
    return context_block + _PLAYBOOK_MD.read_text(encoding="utf-8")


@mcp.tool(title="Save Workflow")
def save_workflow(skeleton: dict, playbooks_by_step: dict) -> dict:
    """Persist a new workflow, its steps, and playbooks.

    skeleton: the JSON object produced by Pass 1 (process skeleton prompt).
    playbooks_by_step: mapping of step name → playbook markdown string.
    """
    result = db.save_workflow(_cfg, skeleton, playbooks_by_step)
    workflow_id = result.pop("id", None)
    for step in result.get("steps", []):
        step.pop("id", None)
        step.pop("workflow_id", None)
    if workflow_id is not None:
        result["monitoring_url"] = _monitoring_url(f"/workflows/{workflow_id}")
    return result


@mcp.tool(title="List Workflows")
def list_workflows() -> dict:
    """Return all workflows with their ordered steps."""
    return {"workflows": db.list_workflows(_cfg), "monitoring_url": _monitoring_url("/workflows")}


@mcp.tool(title="Update Playbook")
def update_playbook(step_id: int, content: str) -> dict:
    """Replace the playbook content for a step."""
    return db.update_playbook(_cfg, step_id, content)


def run(cfg: Config | None = None) -> None:
    """Run the MCP server over stdio. Blocks until the client disconnects."""
    global _cfg
    if cfg is not None:
        _cfg = cfg
    configure_logging()  # routes logs to stderr, never stdout
    mcp.run()  # default transport is stdio
