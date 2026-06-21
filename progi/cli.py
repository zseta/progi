"""Command-line entry point for `progi`.

Run modes
---------
  progi               -> MCP server (stdio) + web UI (background thread)
  progi --no-web      -> MCP server only
  progi-web           -> web UI only (separate entry point, see web.app:main)

Why the web server runs in a background daemon thread in bundled mode:
the MCP server speaks the protocol over stdout and must run in the foreground.
uvicorn is started on a separate thread with logging pinned to stderr so it
never writes to stdout and corrupts the MCP stream. The thread is a daemon, so
it exits when the MCP server (foreground) exits.

Flags override environment variables; environment variables override defaults.
"""

from __future__ import annotations

import argparse
import threading

from . import mcp_server
from .config import Config, load_config
from .logging_setup import configure_logging


def _start_web_in_thread(cfg: Config) -> threading.Thread:
    import uvicorn

    from .web.app import app

    app.state.cfg = cfg
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=cfg.web_host,
            port=cfg.web_port,
            # Keep uvicorn quiet on stdout; warnings/errors go to stderr via our
            # logging config. log_config=None prevents uvicorn from installing
            # its own stdout handlers.
            log_config=None,
            log_level="warning",
        )
    )
    thread = threading.Thread(target=server.run, name="progi-web", daemon=True)
    thread.start()
    return thread


def main() -> None:
    parser = argparse.ArgumentParser(prog="progi", description="progi MCP server + web UI")
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Run only the MCP server (skip the web UI).",
    )
    parser.add_argument("--web-host", default=None, help="Override web bind host.")
    parser.add_argument("--web-port", type=int, default=None, help="Override web port.")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse", "http"],
        help="MCP transport (default: stdio).",
    )
    parser.add_argument("--mcp-host", default="127.0.0.1", help="MCP bind host (sse/http only).")
    parser.add_argument("--mcp-port", type=int, default=8001, help="MCP port (sse/http only).")
    args = parser.parse_args()

    base = load_config()
    cfg = Config(
        db_path=base.db_path,
        web_host=args.web_host or base.web_host,
        web_port=args.web_port or base.web_port,
        no_web=args.no_web or base.no_web,
    )

    configure_logging()

    from .db import init_db

    init_db(cfg)

    if not cfg.no_web:
        _start_web_in_thread(cfg)

    # Foreground: MCP server. Blocks until the client disconnects (stdio) or killed (sse/http).
    mcp_server.run(cfg, transport=args.transport, host=args.mcp_host, port=args.mcp_port)


if __name__ == "__main__":
    main()
