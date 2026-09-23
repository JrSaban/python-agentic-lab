# Todo API

[![CI](https://github.com/JrSaban/python-agentic-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/JrSaban/python-agentic-lab/actions/workflows/ci.yml)

A REST API for managing todos and categories, built with **FastAPI** and **Clean Architecture** in Python. Built as a hands-on way to learn Python, FastAPI and SQLAlchemy, coming from a PHP/Laravel background — every module was written and tested from scratch, including JWT authentication, ownership-based authorization, and a generic repository layer using Python 3.12's native generics.

## Tech stack

- **Python 3.12** · [uv](https://docs.astral.sh/uv/) for dependency management
- **FastAPI** — async web framework, automatic OpenAPI docs
- **SQLAlchemy 2.0** (async) + **Alembic** — ORM and migrations
- **PostgreSQL** (production/dev) · **SQLite/aiosqlite** (tests, in-memory)
- **Pydantic v2** — request/response validation and serialization
- **argon2-cffi** — password hashing · **PyJWT** — token auth
- **pytest** + **httpx** — unit and integration tests
- **Ruff** — linting and formatting
- **Docker Compose** — local dev environment

## Features

- **JWT authentication** — registration, login, `OAuth2PasswordBearer`-based token auth
- **Role-based access control** — regular users vs. admins, with dedicated endpoints to promote/demote or (de)activate accounts (protected against locking out the last remaining admin)
- **Ownership & permissions** — a todo is private to its owner (admins see everything); a category is visible to everyone but only its creator or an admin can edit it, and only an admin can delete it
- **Todos ↔ Categories** — many-to-many relationship, with optional eager-loading (`?include=categories`) and filtering by category
- **Pagination & filtering** — every list endpoint supports `skip`/`limit`, free-text search, and resource-specific filters (status, category, role, ...)
- **Alembic migrations**, including a 3-step pattern (add nullable → backfill → enforce `NOT NULL`) for introducing foreign keys on already-populated tables

## Design highlights

A few decisions worth a second look if you're skimming the code:

- **Ownership lives in the query, not as an afterthought.** `TodoRepository` takes an `owner_id: int | None` filter; the service computes it as `current_user.id`, or `None` for admins to disable the filter entirely. Requesting someone else's todo returns `404`, never `403` — the row simply doesn't match the filter, so the API never confirms whether an ID belongs to another user.
- **Generic repository layer.** `BaseRepository[ModelT: Base]` (`src/core/repository.py`) uses Python 3.12's native generic syntax (`class Foo[T]`) to share `get_by_id`, `update`, `delete`, and pagination across `Todo`, `Category` and `User` repositories, while each resource keeps its own fully-typed filter parameters — no dynamic/untyped filter dicts.
- **Clean Architecture, enforced consistently.** Every module (`todos`, `categories`, `users`, `auth`) follows the same `router → service → repository → models` layering; services raise framework-agnostic exceptions (`NotFoundError`, `ForbiddenError`, ...) mapped to HTTP status codes in one place, never `HTTPException` scattered through the business logic.
- **128 tests**, split between fast unit tests (services tested in isolation with mocked repositories) and integration tests running the full FastAPI stack against a real (in-memory) database.

## Getting started

```bash
git clone https://github.com/JrSaban/python-agentic-lab.git
cd python-agentic-lab
cp .env.example .env

docker compose up -d --build   # API on http://localhost:8000, Postgres on 5432
```

Interactive API docs (Swagger UI) are available at [http://localhost:8000/docs](http://localhost:8000/docs).

<details>
<summary>Running without Docker</summary>

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn src.main:app --reload
```

Requires a Postgres instance reachable at the host/port configured in `.env`.
</details>

## Running the tests

```bash
uv run pytest              # full suite (128 tests)
uv run ruff check .        # lint
uv run ruff format .       # format
```

## API overview

All routes are prefixed with `/api/v1`.

| Method | Path | Description |
|---|---|---|
| `POST` | `/login` | Authenticate, returns a JWT |
| `POST` | `/users` | Register a new account |
| `GET` | `/users/me` | Current user's profile |
| `GET` | `/users` | List users *(admin only)* |
| `GET` `PATCH` | `/users/{id}` | View / update a user |
| `PATCH` | `/users/me/password` | Change your own password |
| `PATCH` | `/users/{id}/active` `/admin` | (De)activate or promote a user *(admin only)* |
| `GET` `POST` | `/todos` | List (own todos, or all for admins) / create a todo |
| `GET` `PATCH` `DELETE` | `/todos/{id}` | View / update / delete a todo you own |
| `GET` `POST` | `/categories` | List / create a category |
| `GET` `PATCH` `DELETE` | `/categories/{id}` | View / update (creator or admin) / delete (admin only) |
| `GET` | `/categories/{id}/todos` | Todos belonging to a category |

## Project structure

```
src/
├── core/            # cross-cutting: database, config, exceptions, security, generic repository
├── modules/
│   ├── auth/        # login, JWT issuance & validation
│   ├── users/        # user profiles, admin management
│   ├── todos/        # todos, ownership
│   ├── categories/   # categories, creator/admin permissions
│   └── todos_categories/  # many-to-many association table
└── main.py
alembic/versions/    # migrations
tests/               # integration tests + tests/unit/ for isolated service tests
```
