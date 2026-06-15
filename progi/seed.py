"""Seed data: a "Blog Post" workflow plus one sample idea converted to a task.

Run with ``python -m progi.seed`` (or ``just seed``). Idempotent: if a workflow
named "Blog Post" already exists, it does nothing. Useful as stable test data
without depending on the AI authoring flow.
"""

from __future__ import annotations

from .config import Config, load_config
from . import db

BLOG_POST_SKELETON: dict = {
    "name": "Blog Post",
    "description": "Workflow for researching, writing, editing, and publishing a blog post.",
    "process": [
        {
            "order": 1,
            "name": "Research",
            "input_spec": {
                "description": "Topic name and any initial notes or reference links the user supplies.",
                "source": "static",
                "from_step": None,
            },
            "output_spec": {
                "type": "file",
                "description": "Research notes covering key points, credible sources, and angles for the post.",
                "constraints": "must be a markdown file",
            },
        },
        {
            "order": 2,
            "name": "Outline",
            "input_spec": {
                "description": "Research notes from the Research step.",
                "source": "previous_step_output",
                "from_step": "Research",
            },
            "output_spec": {
                "type": "file",
                "description": "Structured outline with headings and key bullet points per section.",
                "constraints": "must be a markdown file",
            },
        },
        {
            "order": 3,
            "name": "Draft",
            "input_spec": {
                "description": "Approved outline from the Outline step.",
                "source": "previous_step_output",
                "from_step": "Outline",
            },
            "output_spec": {
                "type": "file",
                "description": "Full first draft of the blog post.",
                "constraints": "must be a markdown file",
            },
        },
        {
            "order": 4,
            "name": "Edit",
            "input_spec": {
                "description": "First draft from the Draft step.",
                "source": "previous_step_output",
                "from_step": "Draft",
            },
            "output_spec": {
                "type": "file",
                "description": "Edited, publish-ready version of the post.",
                "constraints": "must be a markdown file",
            },
        },
        {
            "order": 5,
            "name": "Publish",
            "input_spec": {
                "description": "Final edited post from the Edit step.",
                "source": "previous_step_output",
                "from_step": "Edit",
            },
            "output_spec": {
                "type": "url",
                "description": "Link to the live published post.",
                "constraints": "must be a valid URL",
            },
        },
    ],
}

PLAYBOOKS: dict[str, str] = {
    "Research": """# Step: Research

You are working on the **Research** step of a Blog Post task.
Your goal is to gather enough information on the topic to write a well-informed post.

## Input

The topic name (and any initial notes) were provided when the task was created.
Ask the user for the topic and any seed links or constraints before proceeding if they are not already clear.

## Working instructions

1. Ask the user: "What is the exact topic and target audience? Do you have any reference links or key points you want included?"
2. Wait for the user's reply.
3. Gather information from the provided links plus your own knowledge. Identify 5-8 key points or angles most relevant to the target audience.
4. Assess source credibility; note any conflicting information.

## Output

Save your research notes to `research.md` in the working directory. The file must:
- List the main talking points with short explanations.
- Cite sources with URLs where applicable.
- Note any open questions or gaps.

Report back that `research.md` is ready once saved.""",
    "Outline": """# Step: Outline

You are working on the **Outline** step of a Blog Post task.
Your goal is to turn the research notes into a clear, logical structure for the post.

## Input

The research notes from the previous step are available as `research.md` in the working directory.

## Before you start

Ask the user:
- What is the desired post length (short ~500 w, medium ~1000 w, long ~2000 w)?
- Any sections that must or must not be included?

Wait for the user's reply before proceeding.

## Working instructions

1. Read `research.md` fully.
2. Group related points into 3-6 sections.
3. Order sections for logical flow (context → problem → solution → conclusion, or similar).
4. Write a one-sentence summary of each section.

## Output

Save the outline to `outline.md`. Present it to the user and ask:
"Does this structure look right, or would you like to move/remove/add any sections?"
Iterate until the user approves, then report that `outline.md` is ready.""",
    "Draft": """# Step: Draft

You are working on the **Draft** step of a Blog Post task.
Your goal is to turn the approved outline into a full first draft.

## Input

The approved outline is available as `outline.md` in the working directory.

## Before you start

Ask the user in one message:
- What tone should the post have (casual, technical, formal)?
- Any specific phrasing or terminology to use or avoid?

Wait for their reply before writing.

## Working instructions

1. Follow the outline's section structure exactly.
2. Write full prose for each section—vary sentence length, avoid filler phrases.
3. Include a working title and a short intro paragraph.
4. Aim for the length implied by the Outline step's approved scope.
5. No mid-draft check-ins—write the full draft autonomously based on the instructions above.

## Output

Save the draft to `draft.md`. Report that it is ready; no further approval is needed at this stage (that happens in Edit).""",
    "Edit": """# Step: Edit

You are working on the **Edit** step of a Blog Post task.
Your goal is to turn the first draft into a publish-ready post.

## Input

The first draft is available as `draft.md` in the working directory.

## Working instructions

1. Read the draft end-to-end before making any changes.
2. Fix grammar, punctuation, and spelling errors.
3. Improve sentence flow: split run-ons, vary structure, remove redundancy.
4. Verify the opening paragraph hooks the reader and the conclusion is clear.
5. Ensure headings are consistent and match the outline.
6. No mid-edit check-ins needed—edit autonomously.

## Human review

After editing, present the revised post to the user and ask:
"Here is the edited draft. Does it read well, or are there any sections you would like adjusted?"
Iterate until the user approves.

## Output

Save the final approved version to `edited_post.md` and report it is ready.""",
    "Publish": """# Step: Publish

You are working on the **Publish** step of a Blog Post task.
Your goal is to get the edited post live and capture its URL.

## Input

The final edited post is available as `edited_post.md` in the working directory.

## Working instructions

1. Ask the user: "Where should this post be published (CMS name / URL, or shall I walk you through it)?"
2. Follow the user's publishing workflow—copy/paste content, set metadata (title, tags, publish date) as directed.
3. Confirm with the user once the post is live.

## Output

Once the post is live, ask the user to confirm the public URL.
Report the URL back—this is the step's deliverable.""",
}


CONTENT_REVIEW_SKELETON: dict = {
    "name": "Content Review",
    "description": (
        "Write a draft, then either fast-track to publish (no review needed) "
        "or deep-edit before publishing."
    ),
    "process": [
        {
            "order": 1,
            "name": "Draft",
            "input_spec": {
                "description": "Topic and any initial notes.",
                "source": "static",
                "from_step": None,
            },
            "output_spec": {
                "type": "file",
                "description": "Draft document plus a boolean review_needed field.",
                "constraints": "markdown file; output dict must include review_needed (bool)",
            },
        },
        {
            "order": 2,
            "name": "Quick Publish",
            "input_spec": {
                "description": "Draft from the Draft step.",
                "source": "previous_step_output",
                "from_step": "Draft",
            },
            "output_spec": {
                "type": "url",
                "description": "Published URL (no review required).",
                "constraints": "valid URL",
            },
        },
        {
            "order": 3,
            "name": "Deep Edit",
            "input_spec": {
                "description": "Draft from the Draft step.",
                "source": "previous_step_output",
                "from_step": "Draft",
            },
            "output_spec": {
                "type": "file",
                "description": "Edited, review-ready document.",
                "constraints": "markdown file",
            },
        },
        {
            "order": 4,
            "name": "Publish",
            "input_spec": {
                "description": "Edited document from the Deep Edit step.",
                "source": "previous_step_output",
                "from_step": "Deep Edit",
            },
            "output_spec": {
                "type": "url",
                "description": "Published URL.",
                "constraints": "valid URL",
            },
        },
    ],
    # Draft branches: review_needed=False → Quick Publish (terminal),
    #                 review_needed=True  → Deep Edit → Publish (terminal)
    "edges": [
        {
            "from": "Draft",
            "to": "Quick Publish",
            "condition": {"field": "review_needed", "operator": "eq", "value": False},
            "priority": 0,
        },
        {
            "from": "Draft",
            "to": "Deep Edit",
            "condition": {"field": "review_needed", "operator": "eq", "value": True},
            "priority": 1,
        },
        {
            "from": "Deep Edit",
            "to": "Publish",
            "condition": None,
            "priority": 0,
        },
        # Quick Publish and Publish are terminal (no outgoing edges)
    ],
}

CONTENT_REVIEW_PLAYBOOKS: dict[str, str] = {
    "Draft": """# Step: Draft

Write a draft on the given topic. At the end, decide whether the content
needs editorial review before publishing.

## Output

Submit a dict with:
- `value`: path to the draft file (e.g. `draft.md`)
- `review_needed`: `true` if editorial review is required, `false` to fast-track
""",
    "Quick Publish": """# Step: Quick Publish

Publish the draft directly (no review required).

## Input

The draft file path is in `input_data.value`.

## Output

Submit `{"value": "<published-url>"}`.
""",
    "Deep Edit": """# Step: Deep Edit

Perform a thorough editorial review and polish of the draft.

## Input

The draft file path is in `input_data.value`.

## Output

Submit `{"value": "<edited-file-path>"}`.
""",
    "Publish": """# Step: Publish

Publish the edited document.

## Input

The edited file path is in `input_data.value`.

## Output

Submit `{"value": "<published-url>"}`.
""",
}


def seed(cfg: Config | None = None) -> bool:
    """Create seed workflows + a sample task. Returns False if already seeded."""
    cfg = cfg or load_config()
    existing = {wf["name"] for wf in db.list_workflows(cfg)}

    created_any = False

    if BLOG_POST_SKELETON["name"] not in existing:
        workflow = db.save_workflow(cfg, BLOG_POST_SKELETON, PLAYBOOKS)
        db.create_task(
            cfg,
            "Introduction to ScyllaDB for Developers",
            workflow["id"],
            "A beginner-friendly blog post explaining what ScyllaDB is, how it "
            "compares to Cassandra, and when to use it.",
        )
        created_any = True

    if CONTENT_REVIEW_SKELETON["name"] not in existing:
        db.save_workflow(cfg, CONTENT_REVIEW_SKELETON, CONTENT_REVIEW_PLAYBOOKS)
        created_any = True

    return created_any


def main() -> None:
    from .logging_setup import configure_logging

    configure_logging()
    created = seed()
    # stdout is safe here: this is a standalone script, not the MCP process.
    print("Seeded workflows." if created else "Already seeded; nothing to do.")


if __name__ == "__main__":
    main()
