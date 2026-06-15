# Release Process

## Overview

Releases are managed by [Release Please](https://github.com/googleapis/release-please). After merging commits to `main`, Release Please opens a Release PR that updates `CHANGELOG.md` and bumps the version in `pyproject.toml`. Merging that PR creates a GitHub Release and tag, which triggers the PyPI publish workflow automatically.

**You do not manually edit `CHANGELOG.md` or bump the version** — Release Please does both.

## How it works

```
commit to main → Release Please updates Release PR → merge PR → GitHub Release created → PyPI publish triggered
```

1. Merge PRs to `main` using **squash merge** — edit the squash commit message to follow [Conventional Commits](https://www.conventionalcommits.org/) format (`feat:`, `fix:`, `feat!:` etc.). This is what Release Please reads to determine the version bump and changelog entry.
2. Release Please opens (or updates) a Release PR with the changelog and version bump
3. Review the PR, then merge it when ready to release
4. Release Please creates a GitHub Release and tag (`v*`)
5. The publish workflow triggers on the new release and publishes to PyPI

## Workflows

**`.github/workflows/release-please.yml`** — runs on every push to `main`:
- Opens or updates the Release PR
- Creates a GitHub Release when the Release PR is merged

**`.github/workflows/publish.yml`** — runs when a GitHub Release is published:
1. Builds source distribution and wheel via `uv build`
2. Validates artifacts with `twine check`
3. Publishes to PyPI using trusted publishing (no API token needed)

**`.github/workflows/ci.yml`** — runs on every push to `main` and PRs:
- Lint (`ruff check`)
- Tests (`python -m pytest`)

