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
