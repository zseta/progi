""" """

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..config import load_config
from .routers import board, workflows

_HERE = Path(__file__).parent

app = FastAPI(title="progi")
app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")
app.state.cfg = load_config()
app.state.templates = Jinja2Templates(directory=str(_HERE / "templates"))

app.include_router(board.router)
app.include_router(workflows.router)


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
