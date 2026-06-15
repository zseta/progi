# Contributing to Progi

## Before submitting a PR
Run this:
```bash
uv run ruff check src
uv run python -m pytest
```

Both must pass.

Do not submit code that was not reviewed by you (the human). Make sure that you have a good understanding of the code changes you want to introduce.

If you are using agents to code, we have an `AGENTS.md` you should use.

Do not edit `CHANGELOG.md`. Changelog entries are generated automatically from commit messages by Release Please.

## Commit message format

Use [Conventional Commits](https://www.conventionalcommits.org/) in your PR title and commits:

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

> PRs are squash-merged by maintainers, who will edit the final commit message if needed — so don't stress about getting every commit perfect, just make sure the PR title follows the format.

## Docs & content PRs
You can submit documentation fixes or even new guides/tutorials to share how you use Progi - use cases, workflow examples etc...
