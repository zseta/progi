"""Runtime configuration, resolved from environment variables with sane defaults.

All configuration funnels through here so the MCP server, the web app, and the
CLI agree on the same values (database location, web bind address, etc.).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    # platformdirs gives us OS-appropriate data locations
    # (~/.local/share/progi on Linux, ~/Library/Application Support/progi on
    # macOS, %LOCALAPPDATA%\progi on Windows).
    from platformdirs import user_data_dir

    _DEFAULT_DATA_DIR = Path(user_data_dir("progi", appauthor=False))
except Exception:  # pragma: no cover - platformdirs is a hard dependency, but be safe
    _DEFAULT_DATA_DIR = Path.home() / ".progi"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_db_path() -> Path:
    """Where the SQLite file lives. Override with PROGI_DB_PATH."""
    override = os.environ.get("PROGI_DB_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return (_DEFAULT_DATA_DIR / "progi.db").resolve()


@dataclass(frozen=True)
class Config:
    db_path: Path
    web_host: str
    web_port: int
    # When True, the bundled run mode skips starting the web server.
    no_web: bool

    @property
    def sqlalchemy_url(self) -> str:
        # SQLite URL. The path is absolute so it does not depend on CWD.
        return f"sqlite:///{self.db_path}"

    def ensure_dirs(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    cfg = Config(
        db_path=_resolve_db_path(),
        web_host=os.environ.get("PROGI_WEB_HOST", "127.0.0.1"),
        web_port=int(os.environ.get("PROGI_WEB_PORT", "8000")),
        no_web=_env_bool("PROGI_NO_WEB", default=False),
    )
    return cfg
