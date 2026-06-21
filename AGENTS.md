# AGENTS.md

## What this is

Progi is an MCP-native workflow engine. Key terms:

- **workflow**: a reusable template of ordered **steps**; defines a repeatable, reused across many tasks
- **step**: one unit of work in a workflow; has a **playbook**, an input spec, and an output spec
- **playbook**: markdown attached to a step; the agent reads it via `start_or_continue_task` and follows it
- **task**: a single execution of a workflow; progresses through steps one at a time with lifecycle `todo` → `in_progress` → `done`

Two interfaces over one SQLite DB:

- **Progi MCP server** (FastMCP, stdio) — the work loop runs here, inside the user's harness.
- **Progi Monitoring** (FastAPI + Jinja + Alpine/AlpineAJAX) — a web app for tracking tasks and reviewing workflows.

## The one rule

**All database access goes through `progi/db.py`.** MCP tools and web routes
are thin adapters that call named functions there — they never write SQL. This is
what keeps LLM-driven and human-driven edits behaviorally identical.

## Layout

| File | Role |
|---|---|
| `progi/db.py` | Schema (SQLAlchemy Core) + **all** queries, mutations, and state-transition logic |
| `progi/mcp_server.py` | `@mcp.tool` wrappers (work loop + workflow authoring) |
| `progi/web/app.py` | FastAPI routes → Jinja partials |
| `progi/prompts/` | Pass 1 / Pass 2 authoring system prompts (served by tools) |
| `progi/seed.py` | "Blog Post" workflow + sample task (idempotent) |
| `tests/test_db.py` | DB roundtrip, full work loop, authoring |

## Frontend / UI components

Templates live in `progi/web/templates/`. The UI stack is:

- **Tailwind CSS v4** (compiled by the standalone CLI via `just build`)
- **Alpine.js v3** + **Alpine AJAX** — vendored to `static/vendor/` by `just vendorize`
- **PenguinUI** — a copy-paste component library; no install needed

### Using PenguinUI

Browse components at **https://www.penguinui.com/components**, pick what you need,
and paste the HTML directly into a template. There is nothing to download or import —
PenguinUI components are just Tailwind + Alpine markup.

Key conventions when adding components:
- Use `<article>` as the root for card-style components (PenguinUI's convention).
- Use the existing design tokens from `frontend/input.css` (`bg-surface-*`,
  `text-primary`, `text-accent`, `border-subtle`, etc.) instead of raw colors.
- Interactive components that require Alpine plugins (Collapse, Focus, Mask) must
  vendorize those scripts via `just vendorize` and load them **before** Alpine core
  in `base.html` (plugins must register before Alpine initializes).
- Web routes return **HTML partials** for AJAX; the swapped element's `id` must
  match the `x-target` attribute on the trigger element.

### Adding a new top-level page

Pages live in `progi/web/templates/pages/`. Each page template extends a
variable base template so the same file works for both full page loads and
Alpine AJAX partial swaps — no separate `*_content.html` partial needed.

**1. Template** (`pages/mypage.html`):

```html
{% extends base_template %}

{% block content %}
<!-- page content here -->
{% endblock %}
```

If the page needs full-bleed layout (no max-width wrapper), also override
`outer_class` as an empty block (see `pages/workflows.html`).

**2. Router** (`routers/mypage.py`):

```python
from . import base_template

@router.get("/mypage", response_class=HTMLResponse)
def mypage(request: Request):
    ctx = {"base_template": base_template(request), ...}
    return _templates(request).TemplateResponse(request, "pages/mypage.html", ctx)
```

Always pass `"base_template": base_template(request)` in the context.
`base_template()` returns `"base_partial.html"` for Alpine AJAX requests and
`"base.html"` for direct browser navigation. `base_partial.html` wraps the
content in `<div id="page-content">` so Alpine AJAX can find its swap target.

**3. Nav link** (`base.html`):

```html
<a href="/mypage"
   x-target.push="page-content"
   :class="{ 'text-primary': page === '/mypage', 'text-faint hover:text-muted': page !== '/mypage' }"
   class="text-xs font-medium transition-colors duration-150"
   x-cloak>
  My Page
</a>
```

**4. Register the router** (`web/app.py`):

```python
from .routers import board, mypage, workflows
app.include_router(mypage.router)
```

## Conventions

- **No SQL outside `db.py`.** Add a named function; wrap writes in `with engine.begin()`.
- **Never `print()` / write to stdout** anywhere reachable from the MCP process — stdout is the MCP protocol channel. Log to stderr via `logging_setup`.
- **Web returns HTML partials** for AJAX (not JSON); the swapped element's `id` must match the trigger's `x-target`.
- `input_spec` / `output_spec` / `input_data` / `output` are `sa.JSON` columns — pass and receive plain dicts, no manual `json.dumps`.
- Keep the web UI localhost-only (unauthenticated DB viewer).

### Choosing between fetch + JS state vs. Alpine AJAX partials

Use **plain `fetch` + Alpine reactive state** (in `app.js`) when:
- The backend returns no meaningful body (e.g. 204 on DELETE)
- The UI update is a local state mutation — remove an item, clear a field, reset a flag
- No new HTML needs to come from the server

Use **Alpine AJAX / HTML partials** when:
- The server is the source of truth for what to render (e.g. a detail panel, a refreshed list)
- The response *is* the UI update — swapping in rendered HTML is simpler than rebuilding it in JS

#### Alpine AJAX trigger pattern

Alpine AJAX intercepts clicks on `<a href>` elements and form submits — **not** bare button clicks. For any clickable element that should trigger an AJAX swap, wrap it in an `<a>` tag with `href` pointing to the endpoint and `x-target` naming the element ID to replace:

```html
<a href="/board" x-target="board" class="...">
  Refresh
</a>
```

If you also need to send a payload to backend, use `<FORM>` instead of `<a>`.

Omit `.push` on `x-target` when you don't want the click to update the browser history (e.g. a refresh action vs. navigation).

Example of the fetch pattern (workflow delete in `app.js`):
```js
const resp = await fetch(`/workflows/${id}`, { method: 'DELETE' });
if (resp.ok) {
  this.workflows = this.workflows.filter(wf => wf.id !== id);
  // clear canvas, reset active state, update URL as needed
}
```

## Dev commands

`just` ships in the dev group, so prefix recipes with `uv run` if you don't have a system `just`.

```bash
uv sync --extra dev                  # deps + just
uv run just install                  # + vendored JS, Tailwind CLI
uv run just build                    # compile web/static/style.css
uv run just dev                      # MCP server over SSE (connect via http://127.0.0.1:8001/sse)
uv run just migrate "msg" && uv run just upgrade   # Alembic migration
uv run python -m pytest              # tests (do NOT use `uv run pytest` — a system pytest may shadow it)
uv run ruff check progi              # lint
```

## Run modes

`progi` (MCP + web), `progi --no-web` (MCP only), `progi-web` (web only).
Config via env: `PROGI_DB_PATH`, `PROGI_WEB_HOST`, `PROGI_WEB_PORT`, `PROGI_NO_WEB`.

## Git commit convention
Commit messages must follow Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `ci:`. Use `feat!:` for breaking changes. Release Please reads these to generate the changelog and determine the version bump.

Keep the commit messages short.