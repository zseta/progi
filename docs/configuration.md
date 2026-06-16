# Configuration

## Upgrading to the latest version

To always run the latest published version of Progi, add `--upgrade` to the `args` in your MCP client config:

```json
{
  "mcpServers": {
    "progi": {
      "command": "uvx",
      "args": ["--upgrade", "progi"]
    }
  }
}
```

## Environment variables

All configuration is driven by environment variables. Every setting has a sensible default so no configuration is required to get started.

Set environment variables in the `"env"` block of your MCP client config:

```json
{
  "mcpServers": {
    "progi": {
      "command": "uvx",
      "args": ["progi"],
      "env": {
        "PROGI_DB_PATH": "/path/to/my/progi.db",
        "PROGI_WEB_PORT": "9000"
      }
    }
  }
}
```

## Database path

**Variable:** `PROGI_DB_PATH`

By default, progi stores its SQLite database in the OS-appropriate user data directory:

| OS | Default path |
|---|---|
| Linux | `~/.local/share/progi/progi.db` |
| macOS | `~/Library/Application Support/progi/progi.db` |
| Windows | `%LOCALAPPDATA%\progi\progi.db` |

## Web app

**Variable:** `PROGI_WEB_PORT` — default `8000`

**Variable:** `PROGI_WEB_HOST` — default `127.0.0.1`
