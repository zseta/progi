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
        {"order": 1, "name": "Research"},
        {"order": 2, "name": "Outline"},
        {"order": 3, "name": "Draft"},
        {"order": 4, "name": "Edit"},
        {"order": 5, "name": "Publish"},
    ],
}

PLAYBOOKS: dict[str, str] = {
    "Research": """## Input

`input_data.value` — the topic and any initial notes the user provided when creating the task.

## Instructions

1. Ask the user: "What is the exact topic and target audience? Do you have any reference links or key points you want included?"
2. Wait for the user's reply.
3. Gather information from the provided links plus your own knowledge. Identify 5-8 key points or angles most relevant to the target audience.
4. Assess source credibility; note any conflicting information.
5. Save research notes to `research.md`. The file must list the main talking points with short explanations, cite sources with URLs where applicable, and note any open questions or gaps.

## Human involvement

None required beyond the initial clarification in step 1.

## Output

`research.md` in the working directory. Report back that it is ready once saved.""",
    "Outline": """## Input

`input_data.value` — the file path to the research notes from the previous step (typically `research.md`).

## Instructions

1. Ask the user: "What is the desired post length (short ~500 w, medium ~1000 w, long ~2000 w)? Any sections that must or must not be included?" Wait for their reply.
2. Read `research.md` fully.
3. Group related points into 3-6 sections.
4. Order sections for logical flow (context → problem → solution → conclusion, or similar).
5. Write a one-sentence summary of each section.
6. Save the outline to `outline.md` and present it to the user.

## Human involvement

The user must approve the outline structure before the step is complete. Ask: "Does this structure look right, or would you like to move/remove/add any sections?" Iterate until the user approves.

## Output

`outline.md` — the approved outline. Report that it is ready once the user approves.""",
    "Draft": """## Input

`input_data.value` — the file path to the approved outline from the previous step (typically `outline.md`).

## Instructions

1. Ask the user in one message: "What tone should the post have (casual, technical, formal)? Any specific phrasing or terminology to use or avoid?" Wait for their reply.
2. Follow the outline's section structure exactly.
3. Write full prose for each section — vary sentence length, avoid filler phrases.
4. Include a working title and a short intro paragraph.
5. Aim for the length implied by the Outline step's approved scope.
6. Write the full draft autonomously with no mid-draft check-ins.
7. Save the draft to `draft.md`.

## Human involvement

One upfront question (tone/terminology) before writing. No approval needed at this stage — review happens in the Edit step.

## Output

`draft.md` — the first draft. Report that it is ready.""",
    "Edit": """## Input

`input_data.value` — the file path to the first draft from the previous step (typically `draft.md`).

## Instructions

1. Read the draft end-to-end before making any changes.
2. Fix grammar, punctuation, and spelling errors.
3. Improve sentence flow: split run-ons, vary structure, remove redundancy.
4. Verify the opening paragraph hooks the reader and the conclusion is clear.
5. Ensure headings are consistent and match the outline.
6. Edit autonomously with no mid-edit check-ins.
7. Present the revised post to the user.

## Human involvement

The user must approve the edited post before the step is complete. Ask: "Here is the edited draft. Does it read well, or are there any sections you would like adjusted?" Iterate until the user approves.

## Output

`edited_post.md` — the final approved post. Report that it is ready once the user approves.""",
    "Publish": """## Input

`input_data.value` — the file path to the final edited post from the previous step (typically `edited_post.md`).

## Instructions

1. Ask the user: "Where should this post be published (CMS name / URL, or shall I walk you through it)?"
2. Follow the user's publishing workflow — copy/paste content, set metadata (title, tags, publish date) as directed.
3. Confirm with the user once the post is live.

## Human involvement

The user must provide the publishing destination and confirm the post is live. Ask them to confirm the public URL once published.

## Output

The public URL of the published post. Report it back — this is the step's deliverable.""",
}


CONTENT_REVIEW_SKELETON: dict = {
    "name": "Content Review",
    "description": (
        "Write a draft, then either fast-track to publish (no review needed) "
        "or deep-edit before publishing."
    ),
    "process": [
        {"order": 1, "name": "Draft"},
        {"order": 2, "name": "Quick Publish"},
        {"order": 3, "name": "Deep Edit"},
        {"order": 4, "name": "Publish"},
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
    "Draft": """## Input

`input_data.value` — the topic and any initial notes the user provided when creating the task.

## Instructions

1. Write a draft on the given topic.
2. At the end, decide whether the content needs editorial review before publishing.
3. Save the draft to `draft.md`.

## Human involvement

None required unless the topic is ambiguous — ask for clarification upfront if needed.

## Output

Submit a dict with:
- `value`: path to the draft file (e.g. `draft.md`)
- `review_needed`: `true` if editorial review is required, `false` to fast-track
""",
    "Quick Publish": """## Input

`input_data.value` — the draft file path.

## Instructions

Publish the draft directly without editorial review.

## Human involvement

Ask the user for the publishing destination if not already known. Confirm the post is live before finishing.

## Output

Submit `{"value": "<published-url>"}`.
""",
    "Deep Edit": """## Input

`input_data.value` — the draft file path.

## Instructions

1. Read the draft end-to-end.
2. Fix grammar, punctuation, and spelling errors.
3. Improve sentence flow and remove redundancy.
4. Save the polished version to `edited.md`.

## Human involvement

None required — edit autonomously.

## Output

Submit `{"value": "edited.md"}`.
""",
    "Publish": """## Input

`input_data.value` — the edited file path.

## Instructions

Publish the edited document to the target destination.

## Human involvement

Ask the user for the publishing destination if not already known. Confirm the post is live before finishing.

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
