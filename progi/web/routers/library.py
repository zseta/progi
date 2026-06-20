from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from ... import db
from . import base_template

router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/library", response_class=HTMLResponse)
def library(request: Request):
    cfg = request.app.state.cfg
    entries = db.list_library_entries(cfg)
    ctx = {
        "entries": entries,
        "base_template": base_template(request),
    }
    return _templates(request).TemplateResponse(request, "pages/library.html", ctx)


@router.get("/library/prefill", response_class=JSONResponse)
def library_prefill(request: Request, from_step: int = Query(...)):
    """Return pre-fill data (name + playbook) from an existing step."""
    cfg = request.app.state.cfg
    import sqlalchemy as sa
    from ...models import steps as steps_table
    from ...db import get_engine
    engine = get_engine(cfg)
    with engine.connect() as conn:
        wf_id = conn.execute(
            sa.select(steps_table.c.workflow_id).where(steps_table.c.id == from_step)
        ).scalar()
    if wf_id is None:
        raise HTTPException(status_code=404, detail=f"Step {from_step} not found.")
    try:
        data = db.get_step_detail(cfg, wf_id, from_step)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    step = data["step"]
    return {
        "name": step["name"],
        "playbook": step["playbook"] or "",
    }


@router.get("/library/{entry_id}", response_class=HTMLResponse)
def library_entry(entry_id: int, request: Request):
    """Direct browser navigation — serve full page; JS will open the modal."""
    cfg = request.app.state.cfg
    entries = db.list_library_entries(cfg)
    ctx = {
        "entries": entries,
        "open_entry_id": entry_id,
        "base_template": base_template(request),
    }
    return _templates(request).TemplateResponse(request, "pages/library.html", ctx)


@router.get("/library/{entry_id}/detail", response_class=HTMLResponse)
def library_entry_detail(entry_id: int, request: Request):
    """Return the library entry detail partial for the modal."""
    cfg = request.app.state.cfg
    try:
        entry = db.get_library_entry(cfg, entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    used_by = db.get_library_entry_workflows(cfg, entry_id)
    return _templates(request).TemplateResponse(
        request,
        "partials/library_entry_detail.html",
        {"entry": entry, "used_by": used_by},
    )


@router.post("/library", response_class=JSONResponse)
def create_library_entry(
    request: Request,
    payload: dict = Body(...),
):
    cfg = request.app.state.cfg
    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    playbook = payload.get("playbook", "").strip()
    description = payload.get("description", "").strip()

    from_step = payload.get("from_step")
    try:
        if from_step:
            entry = db.create_library_entry_from_step(cfg, int(from_step), name, description)
        else:
            entry = db.create_library_entry(cfg, name, description, playbook)
    except ValueError as exc:
        status = 409 if "already exists" in str(exc) else 404
        raise HTTPException(status_code=status, detail=str(exc))
    return entry


@router.patch("/library/{entry_id}", status_code=204)
def update_library_entry(
    entry_id: int,
    request: Request,
    payload: dict = Body(...),
):
    cfg = request.app.state.cfg
    try:
        db.update_library_entry(
            cfg,
            entry_id,
            name=payload.get("name"),
            description=payload.get("description"),
            playbook=payload.get("playbook"),
        )
    except ValueError as exc:
        status = 409 if "already exists" in str(exc) else 404
        raise HTTPException(status_code=status, detail=str(exc))
    return Response(status_code=204)


@router.delete("/library/{entry_id}", status_code=204)
def delete_library_entry(entry_id: int, request: Request):
    cfg = request.app.state.cfg
    db.delete_library_entry(cfg, entry_id)
    return Response(status_code=204)
