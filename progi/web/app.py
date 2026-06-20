""" """

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..config import load_config
from .routers import board, library, workflows

_HERE = Path(__file__).parent


def _timeago(value: str | datetime | None) -> str:
    """Return a human-readable relative time string (e.g. '3m ago')."""
    if value is None:
        return ""
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - value
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


app = FastAPI(title="progi")
app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")
app.state.cfg = load_config()
app.state.templates = Jinja2Templates(directory=str(_HERE / "templates"))
app.state.templates.env.filters["timeago"] = _timeago

app.include_router(board.router)
app.include_router(workflows.router)
app.include_router(library.router)


def main() -> None:
    """Entry point for the standalone web server (`progi-web`)."""
    import uvicorn

    from ..logging_setup import configure_logging

    configure_logging()
    from ..db import init_db

    init_db(app.state.cfg)
    uvicorn.run(
        "progi.web.app:app",
        host=app.state.cfg.web_host,
        port=app.state.cfg.web_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
