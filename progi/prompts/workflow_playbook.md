# Workflow Playbook

A workflow playbook is a short document that describes what a workflow does,
what it needs to start, and what it produces when done. It is **authored by the
user** (via the MCP tool `edit_workflow_playbook`) and is stored alongside the
workflow definition.

The workflow playbook serves two roles:

1. **Documentation** — visible on the workflow detail page so humans understand
   the workflow's purpose at a glance.
2. **Sub-workflow context** — when this workflow is embedded as a step inside
   another workflow, the executing sub-agent reads this playbook to orient itself
   before working through the steps.

## Structure

Every workflow playbook must contain exactly these three `##` sections, in this
order. No `#` (h1) heading. Subsections (`###`, `####`) are allowed within each
section.

### `## Purpose`
One sentence describing what this workflow accomplishes. Be concrete — "Produces
a publication-ready blog post from a topic idea" is better than "Handles blog
post creation". Do not list or summarize the steps.

### `## Input`
What the first step receives via `input_data`. Describe the expected format and
fields — for example, "A plain-text topic or title for the blog post", or "A
JSON object with fields `repo_url` and `branch_name`". Focus on the data
contract, not on what the step does with it.

### `## Output`
What the final step writes to its output. Describe the format and fields the
consuming workflow (or human) can expect — for example, "A file path to the
published HTML article", or "A JSON object with `status` and `report_url`
fields". Focus on the data contract, not on how it was produced.

## Example

```markdown
## Purpose
Produces a publication-ready blog post from a topic idea, covering research,
drafting, editing, and publishing.

## Input
A plain-text topic or working title for the blog post (e.g. "The future of
edge computing"). The first step will ask the user for clarification if needed.

## Output
The public URL of the published post as `{"value": "<url>"}`.
```
