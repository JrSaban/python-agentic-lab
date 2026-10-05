# Todo API

[![CI](https://github.com/JrSaban/python-agentic-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/JrSaban/python-agentic-lab/actions/workflows/ci.yml)

A REST API for managing todos and categories, built with **FastAPI** and **Clean Architecture** in Python. Built as a hands-on way to learn Python, FastAPI and SQLAlchemy, coming from a PHP/Laravel background — every module was written and tested from scratch, including JWT authentication with rotating refresh tokens, ownership-based authorization, a Redis cache, and a generic repository layer using Python 3.12's native generics.

## Tech stack

- **Python 3.12** · [uv](https://docs.astral.sh/uv/) for dependency management
- **FastAPI** — async web framework, automatic OpenAPI docs
- **SQLAlchemy 2.0** (async) + **Alembic** — ORM and migrations
- **PostgreSQL** · **Redis** (cache and refresh-token store)
- **Pydantic v2** — request/response validation and serialization
- **argon2-cffi** — password hashing · **PyJWT** — access tokens
- **structlog** — JSON logs with a request ID on every line
- **pytest** + **httpx** — unit and integration tests, on in-memory SQLite and `fakeredis`
- **Ruff** — linting and formatting
- **Docker Compose** · **GitHub Actions**

## Features

- **Authentication** — registration, login, short-lived JWT access tokens, and opaque refresh tokens that are rotated on every use and revoked on logout
- **Role-based access control** — regular users vs. admins, with dedicated endpoints to promote/demote or (de)activate accounts (protected against locking out the last remaining admin)
- **Ownership & permissions** — a todo is private to its owner (admins see everything); a category is visible to everyone but only its creator or an admin can edit it, and only an admin can delete it
- **Todos ↔ Categories** — many-to-many relationship, with optional eager-loading (`?include=categories`) and filtering by category
- **Pagination & filtering** — every list endpoint supports `skip`/`limit`, free-text search, and resource-specific filters (status, category, role, ...)
- **Soft deletes** on todos and categories — a deleted row stays in the database but is invisible to the API, like Laravel's `SoftDeletes`
- **Redis caching** on category reads, invalidated on every write
- **Structured logging** — one JSON line per request, correlated by an `X-Request-ID` header
- **Alembic migrations**, including a 3-step pattern (add nullable → backfill → enforce `NOT NULL`) for introducing foreign keys on already-populated tables

## Design highlights

A few decisions worth a second look if you're skimming the code:

- **Ownership lives in the query, not as an afterthought.** `TodoRepository` takes an `owner_id: int | None` filter; the service computes it as `current_user.id`, or `None` for admins to disable the filter entirely. Requesting someone else's todo returns `404`, never `403` — the row simply doesn't match the filter, so the API never confirms whether an ID belongs to another user.
- **Uniqueness is enforced by the database, not by a check-then-insert.** Category names, emails and pseudos are unique case-insensitively through functional unique indexes (`lower(name)`). Services don't query first: they insert, catch the `IntegrityError`, and return a clean `409` — so two concurrent requests can't both slip through. A dedicated test runs the two inserts concurrently to prove it. The category index is partial (`WHERE deleted_at IS NULL`), so the name of a soft-deleted category can be reused.
- **Refresh tokens are stored hashed and rotated atomically.** Redis only holds the SHA-256 of a token, never the token itself. Each `/refresh` consumes it with a single `GETDEL`, so the same token can't be exchanged twice, even by two requests arriving at the same time. Rotation alone would let an active session renew itself forever, so a separate, longer-lived marker caps the session's absolute lifetime regardless of activity. Changing your password or your email revokes it outright, the same way logging out does.
- **Login takes the same time whether the email exists or not.** An unknown email still runs a full Argon2 verification, against a dummy hash computed once at startup, instead of short-circuiting — otherwise the response time alone would reveal which emails are registered, even behind an identical error message.
- **A cache that never takes the API down.** Paginated category lists are invalidated with a generation counter (one `INCR` instead of hunting for every cached page). Every Redis call on the cache path is allowed to fail: the request falls back to PostgreSQL and logs a warning.
- **Generic repository layer.** `BaseRepository[ModelT: Base]` (`src/core/repository.py`) uses Python 3.12's native generic syntax (`class Foo[T]`) to share `get_by_id`, `update`, `delete`, and pagination across `Todo`, `Category` and `User` repositories, while each resource keeps its own fully-typed filter parameters — no dynamic/untyped filter dicts.
- **Clean Architecture, enforced consistently.** Every module follows the same `router → service → repository → models` layering; services raise framework-agnostic exceptions (`NotFoundError`, `ForbiddenError`, ...) mapped to HTTP status codes in one place, never `HTTPException` scattered through the business logic.
- **Tested at two levels.** Fast unit tests exercise each service in isolation with mocked repositories; integration tests run the full FastAPI stack against a real (in-memory) database. CI also applies every migration to a real PostgreSQL instance.

## Getting started

```bash
git clone https://github.com/JrSaban/python-agentic-lab.git
cd python-agentic-lab
cp .env.example .env
```

Set a real `JWT_SECRET_KEY` in `.env` — the app refuses to start with the placeholder, or with anything shorter than 32 bytes:

```bash
openssl rand -hex 32
```

Then start everything:

```bash
docker compose up -d --build                          # API on :8000, Postgres on :5432, Redis on :6379
docker compose exec api uv run alembic upgrade head   # create the tables
```

Interactive API docs (Swagger UI) are available at [http://localhost:8000/docs](http://localhost:8000/docs).

<details>
<summary>Running the API on the host</summary>

```bash
docker compose up -d db redis
uv sync
uv run alembic upgrade head
uv run uvicorn src.main:app --reload
```

</details>

## Running the tests

No Postgres or Redis needed — the suite runs on in-memory SQLite and `fakeredis`.

```bash
uv run pytest              # full suite
uv run ruff check .        # lint
uv run ruff format .       # format
```

## API overview

All routes are prefixed with `/api/v1`.

| Method | Path | Description |
|---|---|---|
| `POST` | `/login` | Authenticate, returns an access token and a refresh token |
| `POST` | `/refresh` | Exchange a refresh token for a new pair |
| `POST` | `/logout` | Revoke the current refresh token |
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
├── core/            # cross-cutting: database, redis, config, logging, exceptions, security, generic repository
├── modules/
│   ├── auth/        # login, refresh, logout, JWT validation
│   ├── users/        # user profiles, admin management
│   ├── todos/        # todos, ownership
│   ├── categories/   # categories, creator/admin permissions, cache
│   └── todos_categories/  # many-to-many association table
└── main.py          # app, request-ID middleware, exception handlers
alembic/versions/    # migrations
tests/               # integration tests + tests/unit/ for isolated service tests
```

Branch, commit and PR conventions are in [CONTRIBUTING.md](CONTRIBUTING.md).
