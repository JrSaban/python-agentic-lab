# Contributing

## Branch naming

Format: `type/short-description`, lowercase, kebab-case, 2–5 words.

| Type        | Use for                                              |
|-------------|------------------------------------------------------|
| `feat/`     | a new feature (endpoint, filter, module)             |
| `fix/`      | a bug fix                                            |
| `refactor/` | restructuring code without changing behavior         |
| `test/`     | adding or fixing tests only                          |
| `docs/`     | README, CLAUDE.md, docstrings                        |
| `chore/`    | tooling, dependencies, config (ruff, uv, PR template)|
| `ci/`       | GitHub Actions workflows                             |

Examples: `feat/optimistic-locking`, `fix/unique-constraint-race-conditions`, `refactor/base-repository`.

One branch covers one topic. If the name needs an "and", split the branch.

## Commit messages

Short, one line, prefixed with the same type as branches:

```
feat: add version column to todos
fix: catch IntegrityError on category create
```

## Pull requests

- Fill in the PR template: why, changes, how to test.
- Before opening a PR, make sure these pass:

  ```bash
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest
  ```

- If the PR includes an Alembic migration, say so in the "How to test" section (`uv run alembic upgrade head`).

### Stacked PRs

When a branch depends on another unmerged branch (e.g. it needs its migrations), branch off it and open the PR with that branch as its base, not `main`.

- Merge from the bottom up: the PR targeting `main` first.
- Use **Create a merge commit** for stacked PRs. Squash and rebase merges rewrite commit SHAs, so the child PR would need a `git rebase --onto` afterwards.
- Never delete a parent branch manually while a child PR is open. Head branches are deleted automatically after merge, which retargets the child PR to `main`.
