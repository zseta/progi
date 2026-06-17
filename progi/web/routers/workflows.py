from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from ... import db
from . import base_template

router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/workflows", response_class=HTMLResponse)
def workflows(request: Request):
    cfg = request.app.state.cfg
    wf_list = db.list_workflows(cfg)
    ctx = {
        "workflows": wf_list,
        "active_page": "workflows",
        "base_template": base_template(request),
    }
    return _templates(request).TemplateResponse(request, "pages/workflows.html", ctx)


@router.get("/workflows/{workflow_id}", response_class=HTMLResponse)
def workflow_detail(workflow_id: int, request: Request):  # noqa: ARG001
    """Direct browser navigation to a workflow — serve full page; JS selects it."""
    cfg = request.app.state.cfg
    wf_list = db.list_workflows(cfg)
    ctx = {
        "workflows": wf_list,
        "active_page": "workflows",
        "base_template": base_template(request),
    }
    return _templates(request).TemplateResponse(request, "pages/workflows.html", ctx)


@router.get("/workflows/{workflow_id}/graph", response_class=JSONResponse)
def workflow_graph(workflow_id: int, request: Request):
    cfg = request.app.state.cfg
    try:
        wf = db.get_workflow_with_playbooks(cfg, workflow_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return wf


@router.get("/workflows/{workflow_id}/steps/{step_id}", response_class=HTMLResponse)
def step_detail(workflow_id: int, step_id: int, request: Request):
    cfg = request.app.state.cfg
    try:
        data = db.get_step_detail(cfg, workflow_id, step_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Direct browser navigation — serve the full page; the JS deep-link logic
    # will open the modal automatically based on the URL path.
    if not request.headers.get("X-Partial"):
        wf_list = db.list_workflows(cfg)
        return _templates(request).TemplateResponse(
            request,
            "pages/workflows.html",
            {
                "workflows": wf_list,
                "active_page": "workflows",
                "base_template": base_template(request),
            },
        )

    return _templates(request).TemplateResponse(
        request,
        "partials/step_detail.html",
        data,
    )


@router.delete("/workflows/{workflow_id}", status_code=204)
def delete_workflow(workflow_id: int, request: Request):
    cfg = request.app.state.cfg
    try:
        db.delete_workflow(cfg, workflow_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(status_code=204)


@router.patch("/workflows/{workflow_id}/steps/{step_id}")
def update_step(
    workflow_id: int,
    step_id: int,
    request: Request,
    payload: dict = Body(...),
):
    cfg = request.app.state.cfg
    try:
        if "playbook" in payload:
            db.update_playbook(cfg, step_id, payload.pop("playbook"))
        step_fields = {
            k: v for k, v in payload.items() if k in ("name", "input_spec", "output_spec")
        }
        if step_fields:
            db.update_step(cfg, step_id, **step_fields)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(status_code=204)
