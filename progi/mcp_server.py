"""MCP server (FastMCP).

Exposes the AI-native project-management system as MCP tools over stdio. Each tool
is a thin wrapper that delegates to `progi.db` — no business logic or SQL lives
here. Two tool families:

- **Work loop**: create_task, list_tasks,
  start_or_continue_task, update_progress_notes, finish_step.
- **Workflow authoring**: get_process_skeleton_prompt,
  get_playbook_authoring_prompt, save_workflow, list_workflows.

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
_WORKFLOW_PLAYBOOK_MD = _PROMPTS_DIR / "workflow_playbook.md"


# ---------------------------------------------------------------------------
# Work-loop tools
# ---------------------------------------------------------------------------


@mcp.tool(title="Create Task")
def create_task(name: str, workflow_id: int, description: str = "") -> dict:
    """Create a new task under the given workflow.

    Creates the task (status 'todo') and returns the task plus a preview of its
    first step. Before calling this, confirm the workflow choice with the user
    AND ask them what they want to name the task.

    Always show the user the monitoring_url from the response.
    """
    result = db.create_task(_cfg, name, workflow_id, description)
    result["monitoring_url"] = _monitoring_url(f"/tasks/{result['id']}")
    return result


@mcp.tool(title="List Tasks")
def list_tasks(status: str = "", workflow_id: int = 0) -> dict:
    """List tasks, optionally filtered by status and/or workflow_id.

    Empty string / 0 means no filter. "My todos" = status="todo".

    Always show the user the monitoring_url from the response.
    """
    return {
        "tasks": db.list_tasks(_cfg, status, workflow_id),
        "monitoring_url": _monitoring_url("/"),
    }


@mcp.tool(title="Start or Continue Task")
def start_or_continue_task(task_id: int) -> dict:
    """Main work-loop entry point.

    - done        → returns a done message.
    - todo        → starts the task (todo → in_progress) and returns step context.
    - in_progress → returns step context so the agent can resume.

    Context includes task info, the current step name, input_data, the playbook
    markdown, and progress_notes (if any). Follow the playbook's Output section
    for what to produce and how to report it back.

    Always show the user the monitoring_url from the response.
    """
    result = db.start_or_continue_task(_cfg, task_id)
    result["monitoring_url"] = _monitoring_url(f"/tasks/{task_id}")
    return result


@mcp.tool(title="Get Task Context Prompt", output_schema=None)
def get_task_context_prompt(task_id: int) -> str:
    """Return a prompt summarising the completed steps and their output files for a task.

    Call this whenever the user wants to do something with a task outside the
    normal work loop — for example:
    - "I want to edit the draft from task 5"
    - "re-do the AI polish on task 3"
    - "the outline for task 7 needs a new section"
    - "show me what was produced for task 2"

    After calling this tool, read the files referenced in the returned prompt,
    then help the user with whatever they asked.
    """
    return db.get_task_context_prompt(_cfg, task_id)


@mcp.tool(title="Add Adhoc Step Result")
def add_adhoc_step_result(task_id: int, output: dict) -> dict:
    """Record the result of an ad-hoc request as an extra step on the task.

    Call this after completing work triggered by get_task_context_prompt — for
    example, after the user asked you to add a section, revise a draft, or do
    any other extra work outside the normal workflow steps.

    The output dict should include:
    - "name": short description of what was done (e.g. "Added FAQ section")
    - "user_prompt": the exact message the user sent that triggered this work
    - any other relevant fields (file paths, etc.)
    The step will appear in the task's progress history as an ad-hoc step.
    """
    return db.add_adhoc_step_result(_cfg, task_id, output)


@mcp.tool(title="Update Progress Notes")
def update_progress_notes(task_id: int, notes: str) -> dict:
    """Overwrite a task's progress_notes.

    Only call this when the user explicitly asks to save or update progress notes.
    Notes are cleared automatically when a step completes.
    """
    return db.update_progress_notes(_cfg, task_id, notes)


@mcp.tool(title="Finish Step")
def finish_step(task_id: int, output: dict | str, task_name: str = "") -> dict:
    """Mark the current step complete, store its output, and advance.

    Either returns the next step's info (name + playbook, so the agent can
    continue immediately) or {'status': 'done'} if it was the last step.

    Pass task_name to rename the task when you now have enough context to give
    it a meaningful name (e.g. after the first step reveals what the task is
    actually about). Leave it empty to keep the current name.

    IMPORTANT — approval gate: if start_or_continue_task returned
    current_step.requires_approval = true for this step, you MUST present the
    output to the user and ask for explicit approval BEFORE calling this tool.
    Only call finish_step once the user has confirmed they are happy with the
    output. If they request changes, make them first, then ask again.
    """
    if isinstance(output, str):
        if output.strip():
            try:
                output = json.loads(output)
            except json.JSONDecodeError:
                pass  # plain text output — store as-is
        else:
            output = {}
    return db.submit_output(_cfg, task_id, output, task_name or None)


# ---------------------------------------------------------------------------
# Workflow authoring tools
# ---------------------------------------------------------------------------


def _library_block() -> str:
    """Return a markdown section listing all library entries, or empty string if none."""
    entries = db.get_library_entries_summary(_cfg)
    if not entries:
        return ""
    lines = [
        "\n\n## Step Library\n\n"
        "These reusable step playbooks exist in the library. "
        "When a step in the workflow closely matches one, mention it to the user "
        "so they can decide whether to base the playbook on the library entry:\n"
    ]
    for e in entries:
        desc = e["description"] or "(no description)"
        lines.append(f"- **{e['name']}**: {desc}")
    return "\n".join(lines)


@mcp.tool(title="Get Process Skeleton Prompt", output_schema=None)
def get_process_skeleton_prompt() -> str:
    """Return the authoring prompt for designing a new workflow.

    The returned prompt covers both passes:
    - Pass 1: work with the user to produce and approve a skeleton JSON
      (workflow name, description, steps, and edges).
    - Pass 2: once the user approves, generate all step playbooks silently
      (no further tool calls needed) and call save_workflow with everything.
    """
    return _WORKFLOW_SKELETON_MD.read_text(encoding="utf-8") + _library_block()


@mcp.tool(title="Save Workflow")
def save_workflow(skeleton: dict, playbooks_by_step: dict, workflow_playbook: str = "") -> dict:
    """Persist a new workflow, its steps, and playbooks.

    Intended call sequence:
    1. get_process_skeleton_prompt → work with user to produce and approve skeleton JSON.
    2. Generate all step playbooks and the workflow playbook silently using the Pass 2
       instructions in that prompt.
    3. Call save_workflow(skeleton, playbooks_by_step, workflow_playbook) with everything.

    skeleton: the workflow skeleton dict (name, description, steps[]).
              Steps may include "sub_workflow_id": <int> to embed another workflow as a step.
    playbooks_by_step: mapping of step name → playbook markdown string.
                       Omit entries for sub-workflow steps (they have no playbook).
    workflow_playbook: the workflow-level playbook markdown (Purpose / Input / Output sections).
                       Required for workflows that may be used as sub-workflow steps.

    After saving, always show the user the monitoring_url from the response.
    """
    result = db.save_workflow(_cfg, skeleton, playbooks_by_step, workflow_playbook or None)
    workflow_id = result.pop("id", None)
    for step in result.get("steps", []):
        step.pop("id", None)
        step.pop("workflow_id", None)
    if workflow_id is not None:
        result["monitoring_url"] = _monitoring_url(f"/workflows/{workflow_id}")
    return result


@mcp.tool(title="List Workflows")
def list_workflows() -> dict:
    """Return all workflows with their ordered steps.

    Always show the user the monitoring_url from the response.
    """
    return {"workflows": db.list_workflows(_cfg), "monitoring_url": _monitoring_url("/workflows")}


@mcp.tool(title="Get Workflow")
def get_workflow(workflow_id: int) -> dict:
    """Return a workflow's full detail: steps (with order, playbook) and edges.

    Use this as a read step before calling add_step, edit_step, or delete_step
    so you have the current step IDs, order values, and playbook content.
    Do not surface the raw result to the user — the monitoring UI is the right
    place for humans to inspect workflows.
    """
    return db.get_workflow_with_playbooks(_cfg, workflow_id)


@mcp.tool(title="Add Step to Workflow")
def add_step(
    workflow_id: int,
    name: str,
    order: int,
    playbook: str = "",
    requires_approval: bool = False,
    reorder: bool = True,
    sub_workflow_id: int = 0,
) -> dict:
    """Insert a new step into an existing workflow.

    Intended usage:
    1. Call get_workflow(workflow_id) to see current steps and their order values.
    2. Choose an ``order`` value for the new step.
       - If ``reorder=True`` (default) all existing steps with order >= the
         chosen value are shifted up by 1, so the new step slots in cleanly.
         Use this when inserting *between* two consecutive steps.
       - If ``reorder=False`` supply an order value that is already in the gap
         (e.g. between order 10 and 20 use 15).
    3. Before calling this tool, show the user a plain-language preview of the
       change — e.g. "I'll add a new step **Proofread** between **Write Draft**
       and **Publish**." — and wait for their confirmation.
    4. The function rewires edges so the new step is connected to its immediate
       predecessor and successor by order.

    sub_workflow_id: if non-zero, this step embeds another workflow. The step name
                     defaults to the referenced workflow's name. The referenced workflow
                     must have a playbook defined. Mutually exclusive with ``playbook``.

    Returns the newly created step dict.
    """
    return db.add_step_to_workflow(
        _cfg,
        workflow_id=workflow_id,
        name=name,
        order=order,
        playbook=playbook or None,
        requires_approval=requires_approval,
        sub_workflow_id=sub_workflow_id or None,
        reorder=reorder,
    )


@mcp.tool(title="Edit Workflow Playbook")
def edit_workflow_playbook(workflow_id: int, playbook: str = "") -> dict:
    """Set or replace the workflow-level playbook (Purpose / Input / Output).

    The workflow playbook is required for a workflow to be usable as a
    sub-workflow step inside another workflow.

    1. Call get_workflow(workflow_id) to read the current state.
    2. If the user seems unsure about the structure or content, omit `playbook`
       (or pass an empty string) — this returns the authoring guide so you can
       help them draft it before saving.
    3. Once the content is ready, show the user a preview and get confirmation
       if changing an existing playbook.
    4. Call edit_workflow_playbook again with the final markdown content.

    Returns the authoring guide (when playbook is empty) or the updated workflow record.
    """
    if not playbook:
        return {"authoring_guide": _WORKFLOW_PLAYBOOK_MD.read_text()}
    return db.update_workflow_playbook(_cfg, workflow_id, playbook)


@mcp.tool(title="Edit Step")
def edit_step(
    step_id: int,
    name: str | None = None,
    playbook: str | None = None,
    requires_approval: bool | None = None,
) -> dict:
    """Update any combination of fields on an existing step.

    Only the fields you pass (non-None) are changed.  To update the playbook
    pass ``playbook`` as a markdown string — it is upserted so it works whether
    the step has a playbook already or not.

    Intended usage:
    1. Call get_workflow(workflow_id) to find the step ID and current values.
    2. Before calling this tool, show the user a plain-language summary of what
       will change — e.g. "I'll rename **Research** to **Background Research**
       and update its playbook." — and wait for their confirmation.
    3. Call edit_step with only the fields that need to change.

    Returns a dict with the updated step and its current playbook.
    """
    updated_step = db.update_step(
        _cfg,
        step_id,
        name=name,
        requires_approval=requires_approval,
    )
    updated_playbook = None
    if playbook is not None:
        updated_playbook = db.update_playbook(_cfg, step_id, playbook)
    return {"step": updated_step, "playbook": updated_playbook}


@mcp.tool(title="Delete Step")
def delete_step(step_id: int) -> dict:
    """Remove a step from its workflow and reconnect surrounding edges.

    Any edges pointing *to* the deleted step are re-targeted at the step's
    successors, preserving linear connectivity.

    Intended usage:
    1. Call get_workflow(workflow_id) to confirm the step ID you want to remove.
    2. Before calling this tool, tell the user clearly what will be deleted and
       what the new step order will look like afterwards — e.g. "I'll remove
       **QA Review**. The workflow will go directly from **Write Draft** to
       **Publish**." — and wait for their confirmation.
    3. Call delete_step(step_id).

    Returns {"deleted_step_id": step_id, "ok": true}.
    """
    db.delete_step_from_workflow(_cfg, step_id)
    return {"deleted_step_id": step_id, "ok": True}


def run(cfg: Config | None = None, transport: str = "stdio", **transport_kwargs) -> None:
    """Run the MCP server. Blocks until the client disconnects (stdio) or killed (sse/http)."""
    global _cfg
    if cfg is not None:
        _cfg = cfg
    configure_logging()  # routes logs to stderr, never stdout
    mcp.run(transport=transport, **transport_kwargs)
