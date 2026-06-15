# Configuration

All configuration is driven by environment variables. Every setting has a sensible default so no configuration is required to get started.

## Database path

**Variable:** `PROGI_DB_PATH`

By default, progi stores its SQLite database in the OS-appropriate user data directory:

| OS | Default path |
|---|---|
| Linux | `~/.local/share/progi/progi.db` |
| macOS | `~/Library/Application Support/progi/progi.db` |
| Windows | `%LOCALAPPDATA%\progi\progi.db` |

To use a custom location:

```bash
PROGI_DB_PATH=/path/to/my/progi.db progi
```

## Web app

**Variable:** `PROGI_WEB_PORT` — default `8000`

If port 8000 is already in use, override it:

```bash
PROGI_WEB_PORT=9000 progi
```

**Variable:** `PROGI_WEB_HOST` — default `127.0.0.1`

The web UI is bound to localhost only by default. This is intentional — it is an unauthenticated local viewer and should not be exposed on a network interface.

**Variable:** `PROGI_NO_WEB` — default `false`

Set to `1` (or `true`, `yes`, `on`) to start progi without the web server:

```bash
PROGI_NO_WEB=1 progi
```

Alternatively, use the dedicated `progi --no-web` flag or the `progi-web` command to run the web server standalone.
