# Glossary

Terms used across the progi codebase, README, and documentation.

---

## Core concepts

**workflow** — A reusable template for a repeatable process. Made of ordered **steps** connected by **edges**. A workflow is the blueprint; a **task** is a concrete instance of one. Stored in the `workflows` table.

**task** — A piece of work created from a workflow. Advances through steps one at a time and carries a `status` (`todo` / `in_progress` / `done`). Stored in the `tasks` table.

**step** — A single unit of work within a workflow. Ordered, carries an `input_spec` and `output_spec`, and has exactly one **playbook**. Stored in the `steps` table.

**playbook** — A markdown document attached to a step. The AI **agent** reads and follows it to perform the step, including when to involve the human and what output satisfies the `output_spec`. Authored in **Pass 2**. Stored in the `playbooks` table.

**edge** — A directed connection between two steps. Defines execution flow. Can be conditional (evaluated against the step's `output`) or unconditional. Supports branching. Stored in the `step_edges` table.

**agent** — The AI assistant running inside the user's MCP harness (Claude Code, Cursor, etc.). Reads the playbook, performs the work, and calls `finish_step` to advance the task.

---

## Task lifecycle & state

**status** — The current state of a task: `todo` (created, not started), `in_progress` (actively being worked), or `done` (completed).

**step_instance** — A row in `step_instances` tracking the execution of one step within one task. Created lazily when a step is activated. Carries `status` (`pending` / `active` / `complete`), resolved `input_data`, and stored `output`.

**current_step_id** — Foreign key on a task pointing to the step currently being worked. `NULL` when the task is `todo` or `done`.

**entry step** — The first step in a workflow (no incoming edges). Execution starts here.

**terminal step** — A step with no outgoing edges. Reaching one marks the task `done`.

**progress_notes** — Optional mid-step text saved on a task via `update_progress_notes`. Acts as a bookmark so the agent can resume where it left off across sessions. Cleared automatically when a step completes.

---

## Input / output

**input_spec** — A JSON dict on a step describing what data the step needs to begin. Fields: `description`, `source` (`"static"` or `"previous_step_output"`), optional `from_step`. Used at authoring time to tell the agent what inputs are available.

**output_spec** — A JSON dict on a step describing the deliverable that proves the step is done. Fields: `type` (`file` / `url` / `text`), `description`, `constraints`. The agent must produce output matching this spec.

**input_data** — The resolved, concrete data passed to a step instance when it activates. Derived from `input_spec`; may pull from a prior step's `output`. Stored as JSON on `step_instances.input_data`.

**output** — The actual deliverable submitted by the agent via `finish_step`. Stored as JSON on `step_instances.output`. Used to resolve the next step's `input_data` and to evaluate edge `conditions`.

**source** — Field inside `input_spec`. Either `"static"` (data comes from task creation) or `"previous_step_output"` (data comes from a prior step's `output`).

**from_step** — Field inside `input_spec` when `source` is `"previous_step_output"`. Names the step whose output to pull.

---

## Workflow authoring

**Pass 1** — First authoring phase. Converts a plain-language description into a structured **skeleton** (steps, specs, edges). Triggered by `get_process_skeleton_prompt`.

**Pass 2** — Second authoring phase. Authors the **playbook** for each step. Triggered by `get_playbook_authoring_prompt`, which injects full workflow context into the prompt.

**skeleton** — Structured JSON produced in Pass 1: `{ name, description, process: [steps…], edges: [connections…] }`. Each step includes `order`, `name`, `input_spec`, `output_spec`. Reviewed and adjusted before saving.

**condition** — A rule on an edge evaluated against a step's `output` to decide whether that edge is taken. Operators: `eq`, `neq`, `in`, `not_in`. A `null` condition means unconditional (always taken if no other condition matches).

**priority** — Integer on an edge. When a step has multiple outgoing edges, they are evaluated in ascending priority order; the first matching condition wins.

---

## Work loop

**work loop** — The main runtime cycle: `start_or_continue_task` → agent reads playbook and `input_data` → agent works → `finish_step` → next step activates (or task is done). Runs entirely inside the MCP harness.

**lazy creation** — Step instances are created only when a step is activated, not upfront. Avoids instantiating branches that are never taken.

**edge-driven routing** — Next-step selection is determined by evaluating edge conditions against the step's `output`, not by hard-coded logic in the agent or tools.

---

## Architecture

**partial** — An HTML fragment returned by a web route for AJAX replacement via Alpine AJAX. The swapped element's `id` must match the trigger's `x-target` attribute.

**kanban board** — The read-only web UI at `/board`. Shows tasks grouped into three columns by status (`todo` / `in_progress` / `done`).

**seed** — An idempotent script (`seed.py`) that loads demo workflows ("Blog Post", "Content Review") and a sample task. Run via `just seed`.

---

## Run modes

**bundled mode** — Default. Runs MCP server (foreground, stdio) and web UI (background thread) together. Entry point: `progi`.

**MCP-only mode** — MCP server without web UI. Use `--no-web` flag or `PROGI_NO_WEB=1`. Recommended for MCP client configs.

**web-only mode** — Web server without MCP. Entry point: `progi-web`. For a long-lived standalone dashboard.

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `PROGI_DB_PATH` | OS data dir | SQLite file location |
| `PROGI_WEB_HOST` | `127.0.0.1` | Web bind host |
| `PROGI_WEB_PORT` | `8000` | Web port |
| `PROGI_NO_WEB` | `0` | Set to `1` to disable the web UI |
