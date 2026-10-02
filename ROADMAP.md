# Roadmap

This project serves two learning goals at once: transferring backend skills from PHP/Laravel to
Python/FastAPI, and learning to work as an agentic developer — building software in deliberate
collaboration with AI agents and agent-facing tooling (MCP, evals, ...), not just using an
assistant to type faster.

Items are removed once done, as part of the same PR that finishes them. What's already built
lives in the README's Features section and in `CLAUDE.md`, not here.

1. **Security audit follow-ups.** Small fixes from the 2026-10-02 security audit, one branch
   each, in this order. Remove a line when its PR merges, and the whole item with the last one.
   - `fix/debug-default-false` — `Settings.DEBUG` defaults to `False`; `.env.example` keeps
     `True` for development.
   - `fix/revoke-sessions-on-password-change` — `PATCH /users/me/password` revokes the user's
     refresh token, forcing a new login. The revocation becomes a reusable `AuthService` method
     (shared with `logout`), called from the `users` router.
   - `fix/constant-time-login` — `POST /login` runs Argon2 against a dummy hash when the email
     is unknown, so the response time no longer reveals whether an account exists. `POST /users`
     still answers 409 for a taken email; that part stays a known limitation.
   - `feat/email-change-requires-password` — email leaves `UserUpdate`. A user changes their own
     through `PATCH /users/me/email`, which asks for the current password; an admin changes
     someone else's through `PATCH /users/{id}/email`, without a password, and gets a 403 on
     their own ID. Both revoke the target's sessions.
   - `fix/skip-cache-for-name-search` — `GET /categories` is cached only when no `name` filter
     is given, and `skip` gets an upper bound, so a client can't create unlimited cache keys.
     Also caps the length of `category_ids` on todos.
   - `fix/escape-ilike-wildcards` — `%` and `_` typed in a search are matched literally.
2. **Rate limiting.** Redis-backed request throttling, the equivalent of Laravel's `throttle`
   middleware (FastAPI has nothing built in). Starts with `POST /login`, which today accepts
   unlimited password attempts: a counter per email and per IP, answering 429 past a threshold.
   General throttling comes after. Comes before MCP: the API should be hardened against an
   automated/looping consumer before one gets access to it.
3. **Idempotency keys.** An optional, client-generated `Idempotency-Key` header on write
   endpoints, so a retried request can't create a duplicate. Same reasoning as rate limiting —
   protect the API before exposing it to an agent that might retry blindly.
4. **ARQ.** An async, Redis-backed task queue for background jobs. Needs to exist before an MCP
   tool can trigger one.
5. **MCP.** Expose this API as an MCP server with a base set of tools (todos, categories), so an
   agent can act on it directly instead of through a human-facing REST client.
6. **Human-approval gate on an MCP write tool.** A tool that creates a pending change instead of
   applying it directly, requiring a human to approve it first. A small rehearsal of the
   human-validation pattern the next project (a support agent answering from documentation, with
   human approval before sending) will need for real.
7. **Audit log.** Who changed what, when, and whether it was a human or an agent — meaningful
   once there's more than one kind of actor writing to the API. Interacts with soft deletes.
8. **Evals for the MCP tools.** Not "does it work", but "does an agent actually use these tools
   correctly" — including the approval-gated one. Comes last, once the full tool surface exists.
