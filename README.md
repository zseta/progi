# Progi - MCP-native Workflow Engine

<img src="docs/images/logo/progi-logo-small.png" alt="Progi" width="120" />

Progi teaches your agent how **you** like to get things done. So you can do your best work without re-explaining your process or losing context between sessions.


[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/progi)](https://pypi.org/project/progi/)
[![MCP](https://img.shields.io/badge/MCP-compatible-6366f1)](https://modelcontextprotocol.io)

---

## Get started

Add Progi to your MCP client config (GH Copilot / Cursor / Claude Code / etc):

```json
{
  "mcpServers": {
    "progi": {
      "command": "uvx",
      "args": ["progi"]
    }
  }
}
```

Progi Monitoring starts automatically at `http://127.0.0.1:8000`.

If you want to start Monitoring on a different port:
```json
{
  "mcpServers": {
    "progi": {
      "command": "uvx",
      "args": ["progi"],
      "env": {
        "PROGI_WEB_PORT": "8080"
      }
    }
  }
}
```

---

## How it works

**1. Describe your workflow**

*"Hey Progi, help me create workflow for creating integrations, reviewing code, and publishing PRs."*

Describe your process in plain language. You can be detailed or just provide a rough idea. Progi stores it as a structured workflow with per-step playbooks.

**2. Run tasks, stay in the loop**

*"Hey Progi, start a new task, we need to review a new docs PR in the repo."* 
Your agent loads the workflow, works through each step using your playbooks, and loops you in at critical checkpoints to review output.

**3. Monitor progress**

Progi Monitoring gives you a live view of every running and completed task — status, progress, and the full output history across all your workflows.

**4. Optimize as you go**

Tweak playbooks between runs. Because workflows live in a database and survive context resets, every future task picks up your changes automatically — your process gets sharper with each iteration.

---

## MCP Tools

### Work loop

| Tool | Description |
|---|---|
| `create_task` | Create a new task under a given workflow (status `todo`); returns a preview of its first step |
| `list_tasks` | List tasks, optionally filtered by status and/or workflow |
| `start_or_continue_task` | Main work-loop entry point — starts or resumes a task and returns the current step's playbook, input data, and output spec |
| `update_progress_notes` | Overwrite a task's progress notes (mid-step save point) |
| `submit_output` | Mark the current step complete, store its output, and advance to the next step (or mark done) |

### Workflow authoring

| Tool | Description |
|---|---|
| `get_process_skeleton_prompt` | Return the Pass 1 system prompt for turning a plain-language description into a structured workflow skeleton |
| `get_playbook_authoring_prompt` | Return the Pass 2 system prompt for authoring a step's playbook (injects workflow context) |
| `save_workflow` | Persist a new workflow, its steps, and playbooks |
| `list_workflows` | Return all workflows with their ordered steps |
| `update_playbook` | Replace the playbook content for a step |

Authoring is two passes: Pass 1 turns a plain-language description into a structured skeleton; Pass 2 authors each step's playbook. `save_workflow` persists both.

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `PROGI_DB_PATH` | OS data dir (`platformdirs`) | SQLite file location |
| `PROGI_WEB_HOST` | `127.0.0.1` | Web UI bind host |
| `PROGI_WEB_PORT` | `8000` | Web UI port |
| `PROGI_NO_WEB` | `0` | Set to `1` to disable the web UI |

Run modes: `uvx progi` (MCP + web UI), `uvx progi --no-web` (MCP only), `uvx progi-web` (web UI only).

> Use an absolute path for `PROGI_DB_PATH`


<!-- mcp-name: io.github.zseta/progi -->