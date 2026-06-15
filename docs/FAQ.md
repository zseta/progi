# Frequently Asked Questions

## What is Progi?

Progi teaches your agent how **you** like to get things done — so you can do your best work without re-explaining your process or losing context between sessions.

It is an open-source, self-hosted, MCP-native workflow engine that works with any MCP-compatible AI harness: Cursor, Claude Code, OpenCode, Zed, GitHub Copilot, and more.

---

## What are the components of Progi?

Progi ships two components that work together:

- **Progi MCP Server** — the primary interface for agents
- **Progi Monitoring** — a web app for visibility and workflow management

---

## What is Progi MCP Server?

Progi MCP Server is a Model Context Protocol server that gives your AI harness the tools it needs to work with Progi:

- Create and refine workflows
- Create new tasks
- Execute tasks step by step, following your playbooks
- Loop you in at critical checkpoints to review output before continuing

**How it works:**

1. Connect Progi MCP Server to your AI harness.
2. Ask it to do something in natural language — for example: *"Hey Progi, let's start working on a new blog post"* or *"Progi, let's create a workflow for my support ticket process."*

---

## What is Progi Monitoring?

Progi Monitoring is a web application that gives you visibility into your tasks and workflows:

- **Task board** — see the status, progress, and history of all your tasks
- **Workflows** — review and edit your playbooks

> To create workflows or run tasks, use the MCP Server, not Monitoring.

---

## What are the main features of Progi?

- **Persistent workflows** — capture any repeatable process as ordered steps, each with a playbook your agent follows
- **Persistent task execution** — tasks live in a local database, survive context resets, and support long-running work
- **Human-in-the-loop** — let the agent do the heavy lifting and step in only when it matters
- **Task monitoring** — track progress across all your tasks at a glance
- **Workflow optimization** — tweak and refine workflows over time until they are exactly right

---

## What is a "workflow"?

A workflow is an ordered list of steps. Each step has:

- **Playbook** (markdown) — instructions the agent follows during execution
- **Input spec** (JSON) — data the agent needs to start the step
- **Output spec** (JSON) — data the agent must produce to complete the step

When you ask the agent to work on a task, it will:

1. Load the steps of the workflow
2. Complete each step in order, guided by the playbook and specs
3. Pause for your approval where required — between steps or even mid-step

---

## What kinds of workflows can I run with Progi?

Progi supports a wide range of workflow patterns. Because the agent follows whatever instructions are in the playbook, the workflow type is determined by how you write it — not by special engine features:

- **Sequential** — Step A → B → C
- **Branching / conditional** — the path diverges based on the output of a step (if/else, switch-case routing)
- **Loop / iterative** — a step repeats until a condition is met
- **Human-in-the-loop** — the workflow pauses for manual approval before continuing
- **Hierarchical / sub-workflow** — a step invokes a nested workflow

Because Progi is generic, you can model virtually any process your AI harness is capable of executing.

---

## How do I create a workflow?

After connecting Progi MCP Server, just describe your process in plain language. There are two paths:

- **Detailed process** — hand it to Progi and it saves the workflow as-is.
- **Rough idea** — Progi helps you design a high-level skeleton first. Once you are happy with the structure, it generates detailed playbooks for each step for your review and approval.

You can also edit individual step playbooks at any time from Progi Monitoring.

---

## How is Progi different from just giving the AI a prompt?

A prompt disappears after one session. Progi makes your workflow persist: it lives in a local database, survives context resets, and produces a record of what was done and what output was generated at each step. You define the process once and reuse it across many tasks — and refine it over time as you learn what works.

---

## Does Progi replace my AI assistant?

No. Progi runs alongside your AI harness as an MCP server. Your AI calls Progi's tools to read the next step, do the work, and submit output. Progi is the memory and structure layer; your AI does the actual work.

---

## What is a "playbook"?

A playbook is a markdown document attached to a workflow step. It tells the agent exactly what to do at that step. When the agent calls `start_or_continue_task`, Progi returns the current step's playbook as the agent's instructions.

---

## Where is my data stored?

In a local SQLite file on your machine. Progi does not send any of your data to external services — it is just an MCP server connected to a locally hosted database.

---

## Can I use Progi with GitHub Copilot, Cursor, Zed, or others — not just Claude Code?

Yes. Progi exposes a standard MCP interface, so any MCP-compatible client works.

---

## What technologies does Progi use under the hood?

- **MCP Server** — Python (FastMCP)
- **Monitoring web app** — Python (FastAPI + Jinja2) with Alpine.js on the frontend
- **Database** — SQLite
