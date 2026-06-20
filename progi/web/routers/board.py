from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ... import db
from . import base_template

router = APIRouter()


def _templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    cfg = request.app.state.cfg
    ctx = {
        "tasks": db.board_tasks(cfg),
        "active_page": "board",
        "base_template": base_template(request),
    }
    return _templates(request).TemplateResponse(request, "pages/board.html", ctx)


@router.get("/board", response_class=HTMLResponse)
def board(request: Request):
    """Return just the board partial (used to refresh after changes)."""
    cfg = request.app.state.cfg
    return _templates(request).TemplateResponse(
        request,
        "partials/board.html",
        {"tasks": db.board_tasks(cfg)},
    )


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
def task_detail(task_id: int, request: Request):
    cfg = request.app.state.cfg
    try:
        data = db.get_task_detail(cfg, task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    # Direct browser navigation — serve the full board page; JS deep-link logic
    # will open the modal automatically based on the URL path.
    if not request.headers.get("X-Partial"):
        return _templates(request).TemplateResponse(
            request,
            "pages/board.html",
            {
                "tasks": db.board_tasks(cfg),
                "active_page": "board",
                "base_template": base_template(request),
            },
        )

    return _templates(request).TemplateResponse(
        request,
        "partials/task_detail.html",
        data,
    )
