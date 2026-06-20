"""Smoke + work-loop tests for the AI-native task system."""

import os
import tempfile
from contextlib import contextmanager


@contextmanager
def _fresh_db(monkeypatch):
    """Yield a Config bound to a throwaway SQLite file with the schema created."""
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setenv("PROGI_DB_PATH", os.path.join(d, "t.db"))
        from progi.config import load_config
        from progi.db import metadata, get_engine, dispose_engine

        cfg = load_config()
        metadata.create_all(get_engine(cfg))
        try:
            yield cfg
        finally:
            dispose_engine()


def _seed(cfg):
    from progi import seed

    assert seed.seed(cfg) is True
    from progi import db

    wf = db.list_workflows(cfg)[0]
    task = db.list_tasks(cfg)[0]
    return wf, task


def test_full_work_loop(monkeypatch):
    with _fresh_db(monkeypatch) as cfg:
        from progi import db

        _, task = _seed(cfg)
        task_id = task["id"]
        assert task["status"] == "todo"

        # First pickup flips todo -> in_progress and returns step context.
        ctx = db.start_or_continue_task(cfg, task_id)
        assert ctx["task"]["status"] == "in_progress"
        assert ctx["current_step"]["name"] == "Research"
        assert ctx["current_step"]["playbook"].startswith("# Step: Research")

        # Advance through all 5 steps.
        step_names = ["Research", "Outline", "Draft", "Edit", "Publish"]
        for i, name in enumerate(step_names):
            result = db.submit_output(
                cfg, task_id, {"type": "file", "value": f"out-{i}.md"}
            )
            if i < 4:
                assert result["status"] == "in_progress"
                assert result["next_step"]["name"] == step_names[i + 1]
                # Inputs after step 0 resolve from the previous output.
                assert result["next_step"]["input_data"]["value"] == f"out-{i}.md"
            else:
                assert result["status"] == "done"

        # Task is now done; start_or_continue reports it.
        done = db.start_or_continue_task(cfg, task_id)
        assert done["status"] == "done"


def test_double_submit_after_done_raises(monkeypatch):
    with _fresh_db(monkeypatch) as cfg:
        import pytest
        from progi import db

        _, task = _seed(cfg)
        task_id = task["id"]
        db.start_or_continue_task(cfg, task_id)
        for _ in range(5):
            db.submit_output(cfg, task_id, {"type": "file", "value": "x"})
        with pytest.raises(ValueError):
            db.submit_output(cfg, task_id, {"type": "file", "value": "x"})


def test_progress_notes_roundtrip(monkeypatch):
    with _fresh_db(monkeypatch) as cfg:
        from progi import db

        _, task = _seed(cfg)
        task_id = task["id"]
        db.start_or_continue_task(cfg, task_id)
        db.update_progress_notes(cfg, task_id, "stopped mid-research")

        resumed = db.start_or_continue_task(cfg, task_id)
        assert resumed["progress_notes"] == "stopped mid-research"

        # Completing a step clears the notes.
        db.submit_output(cfg, task_id, {"type": "file", "value": "research.md"})
        after = db.start_or_continue_task(cfg, task_id)
        assert "progress_notes" not in after


def test_authoring_roundtrip(monkeypatch):
    with _fresh_db(monkeypatch) as cfg:
        from progi import db

        skeleton = {
            "name": "Tiny",
            "description": "two-step workflow",
            "process": [
                {
                    "order": 1,
                    "name": "A",
                    "input_spec": {"description": "start", "source": "static"},
                    "output_spec": {"type": "text", "description": "out", "constraints": ""},
                },
                {
                    "order": 2,
                    "name": "B",
                    "input_spec": {
                        "description": "from A",
                        "source": "previous_step_output",
                        "from_step": "A",
                    },
                    "output_spec": {"type": "text", "description": "out", "constraints": ""},
                },
            ],
        }
        wf = db.save_workflow(cfg, skeleton, {"A": "playbook A", "B": "playbook B"})
        assert len(wf["steps"]) == 2

        listed = db.list_workflows(cfg)
        assert listed[0]["name"] == "Tiny"
        assert len(listed[0]["steps"]) == 2

        renamed = db.update_workflow(cfg, wf["id"], "Tiny v2")
        assert renamed["name"] == "Tiny v2"

        step_a_id = wf["steps"][0]["id"]
        db.update_playbook(cfg, step_a_id, "playbook A v2")
        ctx = db.get_playbook_authoring_context(cfg, step_a_id)
        assert ctx["workflow"]["name"] == "Tiny v2"
        assert len(ctx["siblings"]) == 2


def test_save_workflow_without_edges_creates_linear(monkeypatch):
    """Saving a skeleton without an 'edges' key auto-generates linear edges."""
    with _fresh_db(monkeypatch) as cfg:
        from progi import db
        from progi.db import get_engine
        from progi.models import step_edges
        import sqlalchemy as sa

        skeleton = {
            "name": "Linear",
            "description": "three steps, no edges key",
            "process": [
                {"order": 1, "name": "A", "input_spec": {"source": "static", "description": "x"}, "output_spec": {"type": "text", "description": "x", "constraints": ""}},
                {"order": 2, "name": "B", "input_spec": {"source": "static", "description": "x"}, "output_spec": {"type": "text", "description": "x", "constraints": ""}},
                {"order": 3, "name": "C", "input_spec": {"source": "static", "description": "x"}, "output_spec": {"type": "text", "description": "x", "constraints": ""}},
            ],
        }
        wf = db.save_workflow(cfg, skeleton, {})
        engine = get_engine(cfg)
        with engine.connect() as conn:
            edges = conn.execute(
                sa.select(step_edges).where(step_edges.c.workflow_id == wf["id"])
            ).mappings().all()
        # 3 steps → 2 edges (A→B, B→C)
        assert len(edges) == 2
        step_ids = [s["id"] for s in wf["steps"]]
        assert edges[0]["from_step_id"] == step_ids[0]
        assert edges[0]["to_step_id"] == step_ids[1]
        assert edges[1]["from_step_id"] == step_ids[1]
        assert edges[1]["to_step_id"] == step_ids[2]


def test_branching_false_path(monkeypatch):
    """review_needed=False → Quick Publish → done (skips Deep Edit)."""
    with _fresh_db(monkeypatch) as cfg:
        from progi import seed, db

        seed.seed(cfg)
        wfs = {wf["name"]: wf for wf in db.list_workflows(cfg)}
        wf = wfs["Content Review"]
        task = db.create_task(cfg, "Test article", wf["id"])
        task_id = task["id"]

        db.start_or_continue_task(cfg, task_id)

        # Submit Draft with review_needed=False → should go to Quick Publish
        result = db.submit_output(cfg, task_id, {"value": "draft.md", "review_needed": False})
        assert result["status"] == "in_progress"
        assert result["next_step"]["name"] == "Quick Publish"

        # Submit Quick Publish → terminal, task done
        result = db.submit_output(cfg, task_id, {"value": "https://example.com/post"})
        assert result["status"] == "done"


def test_branching_true_path(monkeypatch):
    """review_needed=True → Deep Edit → Publish → done (skips Quick Publish)."""
    with _fresh_db(monkeypatch) as cfg:
        from progi import seed, db

        seed.seed(cfg)
        wfs = {wf["name"]: wf for wf in db.list_workflows(cfg)}
        wf = wfs["Content Review"]
        task = db.create_task(cfg, "Test article", wf["id"])
        task_id = task["id"]

        db.start_or_continue_task(cfg, task_id)

        # Submit Draft with review_needed=True → should go to Deep Edit
        result = db.submit_output(cfg, task_id, {"value": "draft.md", "review_needed": True})
        assert result["status"] == "in_progress"
        assert result["next_step"]["name"] == "Deep Edit"

        # Submit Deep Edit → should go to Publish
        result = db.submit_output(cfg, task_id, {"value": "edited.md"})
        assert result["status"] == "in_progress"
        assert result["next_step"]["name"] == "Publish"

        # Submit Publish → terminal, task done
        result = db.submit_output(cfg, task_id, {"value": "https://example.com/post"})
        assert result["status"] == "done"


def test_no_matching_condition_raises(monkeypatch):
    """When all edges are conditional and none match, ValueError is raised."""
    with _fresh_db(monkeypatch) as cfg:
        import pytest
        from progi import db
        from progi.db import get_engine
        from progi.models import step_edges
        import sqlalchemy as sa

        # Create a 2-step workflow where the edge has a condition that won't match
        skeleton = {
            "name": "Strict",
            "description": "conditional edge, no fallback",
            "process": [
                {"order": 1, "name": "A", "input_spec": {"source": "static", "description": "x"}, "output_spec": {"type": "text", "description": "x", "constraints": ""}},
                {"order": 2, "name": "B", "input_spec": {"source": "static", "description": "x"}, "output_spec": {"type": "text", "description": "x", "constraints": ""}},
            ],
            "edges": [
                {"from": "A", "to": "B", "condition": {"field": "go", "operator": "eq", "value": True}, "priority": 0},
            ],
        }
        wf = db.save_workflow(cfg, skeleton, {})
        task = db.create_task(cfg, "test", wf["id"])
        db.start_or_continue_task(cfg, task["id"])

        # Output doesn't include go=True → no edge matches → ValueError
        with pytest.raises(ValueError, match="No outgoing edge condition matched"):
            db.submit_output(cfg, task["id"], {"value": "something"})


def test_delete_workflow(monkeypatch):
    with _fresh_db(monkeypatch) as cfg:
        import pytest
        from progi import db

        # Save a fresh workflow with no tasks so FK cascade isn't blocked
        skeleton = {
            "name": "Disposable",
            "description": "will be deleted",
            "process": [
                {"order": 1, "name": "Only", "input_spec": {"source": "static", "description": "x"}, "output_spec": {"type": "text", "description": "x", "constraints": ""}},
            ],
        }
        wf = db.save_workflow(cfg, skeleton, {})
        db.delete_workflow(cfg, wf["id"])
        assert all(w["id"] != wf["id"] for w in db.list_workflows(cfg))
        with pytest.raises(ValueError):
            db.delete_workflow(cfg, wf["id"])


def test_create_task_with_description_and_get_detail(monkeypatch):
    with _fresh_db(monkeypatch) as cfg:
        from progi import db

        wf, _ = _seed(cfg)
        task = db.create_task(cfg, "My task", wf["id"], description="some context")
        assert task["description"] == "some context"
        assert task["first_step"]["name"] == "Research"

        detail = db.get_task_detail(cfg, task["id"])
        assert detail["task"]["name"] == "My task"
        assert detail["task"]["description"] == "some context"


def test_list_tasks_filtering(monkeypatch):
    with _fresh_db(monkeypatch) as cfg:
        from progi import db

        wf, seed_task = _seed(cfg)
        task2 = db.create_task(cfg, "Second", wf["id"])

        # Status filter
        todo = db.list_tasks(cfg, status="todo")
        assert all(t["status"] == "todo" for t in todo)
        assert len(todo) == 2

        db.start_or_continue_task(cfg, seed_task["id"])
        in_prog = db.list_tasks(cfg, status="in_progress")
        assert len(in_prog) == 1 and in_prog[0]["id"] == seed_task["id"]

        # workflow_id filter
        by_wf = db.list_tasks(cfg, workflow_id=wf["id"])
        assert {t["id"] for t in by_wf} == {seed_task["id"], task2["id"]}

        # Both filters combined
        combined = db.list_tasks(cfg, status="todo", workflow_id=wf["id"])
        assert len(combined) == 1 and combined[0]["id"] == task2["id"]


def test_update_step(monkeypatch):
    with _fresh_db(monkeypatch) as cfg:
        from progi import db

        skeleton = {
            "name": "Edit me",
            "description": "one step",
            "process": [
                {"order": 1, "name": "Alpha", "input_spec": {"source": "static", "description": "x"}, "output_spec": {"type": "text", "description": "x", "constraints": ""}},
            ],
        }
        wf = db.save_workflow(cfg, skeleton, {})
        step_id = wf["steps"][0]["id"]

        updated = db.update_step(
            cfg,
            step_id,
            name="Alpha Renamed",
            input_spec={"source": "static", "description": "updated"},
        )
        assert updated["name"] == "Alpha Renamed"
        assert updated["input_spec"]["description"] == "updated"
        # output_spec unchanged
        assert updated["output_spec"]["type"] == "text"


def test_board_tasks(monkeypatch):
    with _fresh_db(monkeypatch) as cfg:
        from progi import db

        _, task = _seed(cfg)
        board = db.board_tasks(cfg)
        assert isinstance(board, list)
        assert any(t["id"] == task["id"] for t in board)

        db.start_or_continue_task(cfg, task["id"])
        board = db.board_tasks(cfg)
        assert any(t["id"] == task["id"] for t in board)


def _make_one_step_workflow(db, cfg, name="Lib Test", playbook_content="# My Playbook"):
    skeleton = {
        "name": name,
        "description": "for library tests",
        "process": [
            {"order": 1, "name": "Only", "input_spec": {"source": "static", "description": "x"}, "output_spec": {"type": "text", "description": "x", "constraints": ""}},
        ],
    }
    wf = db.save_workflow(cfg, skeleton, {"Only": playbook_content})
    return wf


def test_create_library_entry_from_step(monkeypatch):
    with _fresh_db(monkeypatch) as cfg:
        from progi import db

        wf = _make_one_step_workflow(db, cfg, playbook_content="# Step Playbook")
        step_id = wf["steps"][0]["id"]

        entry = db.create_library_entry_from_step(cfg, step_id, "My Entry", "A description")
        assert entry["name"] == "My Entry"
        assert entry["description"] == "A description"
        assert entry["playbook"] == "# Step Playbook"

        # Step should now be linked back to the entry
        linked = db.get_library_entry_workflows(cfg, entry["id"])
        assert len(linked) == 1
        assert linked[0]["step_id"] == step_id


def test_get_library_entry_workflows(monkeypatch):
    with _fresh_db(monkeypatch) as cfg:
        from progi import db
        from progi.db import get_engine
        from progi.models import steps
        import sqlalchemy as sa

        entry = db.create_library_entry(cfg, "Shared Entry", "desc", "# Shared")

        wf1 = _make_one_step_workflow(db, cfg, name="WF1")
        wf2 = _make_one_step_workflow(db, cfg, name="WF2")
        step1_id = wf1["steps"][0]["id"]
        step2_id = wf2["steps"][0]["id"]

        engine = get_engine(cfg)
        with engine.begin() as conn:
            conn.execute(sa.update(steps).where(steps.c.id == step1_id).values(library_entry_id=entry["id"]))
            conn.execute(sa.update(steps).where(steps.c.id == step2_id).values(library_entry_id=entry["id"]))

        results = db.get_library_entry_workflows(cfg, entry["id"])
        assert len(results) == 2
        step_ids = {r["step_id"] for r in results}
        assert step_ids == {step1_id, step2_id}
        wf_names = {r["workflow_name"] for r in results}
        assert wf_names == {"WF1", "WF2"}


def test_delete_library_entry_nullifies_step_fk(monkeypatch):
    with _fresh_db(monkeypatch) as cfg:
        from progi import db
        from progi.db import get_engine
        from progi.models import steps
        import sqlalchemy as sa

        wf = _make_one_step_workflow(db, cfg, playbook_content="# pb")
        step_id = wf["steps"][0]["id"]
        entry = db.create_library_entry_from_step(cfg, step_id, "To Delete", "desc")

        db.delete_library_entry(cfg, entry["id"])

        engine = get_engine(cfg)
        with engine.connect() as conn:
            row = conn.execute(
                sa.select(steps.c.library_entry_id).where(steps.c.id == step_id)
            ).scalar()
        assert row is None


def test_get_library_entries_summary(monkeypatch):
    with _fresh_db(monkeypatch) as cfg:
        from progi import db

        db.create_library_entry(cfg, "Beta", "desc B", "# B")
        db.create_library_entry(cfg, "Alpha", "desc A", "# A")

        summary = db.get_library_entries_summary(cfg)
        assert summary == [
            {"name": "Alpha", "description": "desc A"},
            {"name": "Beta", "description": "desc B"},
        ]


def test_web_app_builds(monkeypatch):
    with _fresh_db(monkeypatch):
        from progi.web.app import app

        assert app.title == "progi"
