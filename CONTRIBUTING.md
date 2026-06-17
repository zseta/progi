# Contributing to Progi

## Normal Git flow
1. Fork the repository on GitHub.
1. Create a new branch in your fork.
1. Make your changes
1. Run this:
  ```bash
  uv run ruff check progi
  uv run python -m pytest
  ```
  Both must pass.
1. Commit changes
1. Push your branch and open a pull request.

If you are using agents to code, we have an `AGENTS.md` you should use.

Do not edit `CHANGELOG.md`. Changelog entries are generated automatically from commit messages by Release Please.

## PR title format
Use [Conventional Commits](https://www.conventionalcommits.org/) in your PR title:

```
<type>: <description>
```

Common types:

| Type | When to use |
|---|---|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `refactor:` | Code change that's neither a fix nor a feature |
| `test:` | Adding or updating tests |
| `chore:` | Maintenance, dependencies, tooling |

For breaking changes, add `!` after the type: `feat!: rename task API`.


## Docs & content PRs
You can submit documentation fixes or even new guides/tutorials to share how you use Progi - use cases, workflow examples etc...
