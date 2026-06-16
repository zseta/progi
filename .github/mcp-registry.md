# Publishing to the MCP Registry

Progi is listed on the [MCP Registry](https://registry.modelcontextprotocol.io). The registry entry lives in [`.github/server.json`](server.json).

## Versioning

`server.json` has two version fields that must be kept in sync with the PyPI release:

| Field | Example | Meaning |
|---|---|---|
| `version` (top-level) | `0.3.2-registry.1` | Registry entry version — bump the `-registry.N` suffix for registry-only changes, or reset to `-registry.1` on a new PyPI release |
| `packages[0].version` | `0.3.2` | Must match the PyPI package version exactly |

Both are updated automatically by the `update-server-json` GitHub Actions workflow whenever a new version is published to PyPI.

## Manual publish / update

### 1. Install the publisher CLI

```bash
git clone https://github.com/modelcontextprotocol/registry
cd registry
make publisher
```

### 2. Edit `server.json`

Bump `version` (top-level) if you need to push a registry-only change without a new PyPI release.

### 3. Publish

```bash
./bin/mcp-publisher login github
./bin/mcp-publisher publish
```
