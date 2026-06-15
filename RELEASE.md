# Release Process

## Overview

Publishing to PyPI is automated via GitHub Actions. Pushing a `v*` tag triggers the publish workflow. There is no manual `uv publish` step.

## Steps

### 1. Make your changes

Do your work on `main` (or merge a PR into `main`).

### 2. Update the version

In `pyproject.toml`:

```toml
version = "0.2.0"
```

Follow [Semantic Versioning](https://semver.org/):

| Change | Bump |
|---|---|
| Bug fixes, metadata-only changes | Patch (`0.1.0` → `0.1.1`) |
| New features, backwards-compatible | Minor (`0.1.0` → `0.2.0`) |
| Breaking changes | Major (`0.1.0` → `1.0.0`) |

### 3. Update CHANGELOG.md

Add a new section at the top (above the previous release):

```markdown
## [0.2.0] - YYYY-MM-DD

### Added
- ...

### Changed
- ...

### Fixed
- ...

[0.2.0]: https://github.com/zseta/progi/releases/tag/v0.2.0
```

### 4. Commit

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore: release v0.2.0"
```

### 5. Tag and push

```bash
git tag v0.2.0
git push origin main --tags
```

Pushing the `v*` tag triggers the publish workflow automatically.

## What the workflow does

`.github/workflows/publish.yml` runs on any `v*` tag:

1. Builds the source distribution and wheel via `uv build`
2. Validates the dist artifacts with `twine check`
3. Publishes to PyPI using trusted publishing (no API token needed)

CI (`.github/workflows/ci.yml`) runs lint + tests on every push to `main` and on pull requests — make sure it passes before tagging.

## PyPI metadata

All package metadata lives in `pyproject.toml` under `[project]`.

`version` — bump this each release