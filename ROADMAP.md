# Roadmap

This project serves two learning goals at once: transferring backend skills from PHP/Laravel to
Python/FastAPI, and learning to work as an agentic developer — building software in deliberate
collaboration with AI agents and agent-facing tooling (MCP, evals, ...), not just using an
assistant to type faster.

Items are removed once done, as part of the same PR that finishes them. What's already built
lives in the README's Features section and in `CLAUDE.md`, not here.

1. **Idempotency keys.** An optional, client-generated `Idempotency-Key` header on write
   endpoints, so a retried request can't create a duplicate. Same reasoning as rate limiting —
   protect the API before exposing it to an agent that might retry blindly.
2. **ARQ.** An async, Redis-backed task queue for background jobs. Needs to exist before an MCP
   tool can trigger one.
3. **Pruning soft-deleted rows.** The equivalent of Laravel's `Prunable` + `model:prune`, run as a
   scheduled ARQ job: todos and categories soft-deleted for longer than a retention period are
   deleted for good, together with their `todos_categories` associations. The period is a
   setting (`SOFT_DELETE_RETENTION_DAYS`, 30 by default), shared by both models for now. The
   first real job for ARQ, so it comes right after it.
4. **MCP.** Expose this API as an MCP server with a base set of tools (todos, categories), so an
   agent can act on it directly instead of through a human-facing REST client.
5. **Human-approval gate on an MCP write tool.** A tool that creates a pending change instead of
   applying it directly, requiring a human to approve it first. A small rehearsal of the
   human-validation pattern the next project (a support agent answering from documentation, with
   human approval before sending) will need for real.
6. **Audit log.** Who changed what, when, and whether it was a human or an agent — meaningful
   once there's more than one kind of actor writing to the API. Interacts with soft deletes, and must not depend on rows that pruning will eventually remove.
7. **Evals for the MCP tools.** Not "does it work", but "does an agent actually use these tools correctly" — including the approval-gated one. Comes last, once the full tool surface exists.
8. **Client IP behind a reverse proxy.** The rate limits identify anonymous clients by
   `request.client.host`. Behind a reverse proxy (Nginx, a load balancer, a hosting platform),
   that is the proxy's address, so every anonymous client would share one counter: a single busy
   client would put everyone in 429, and the login IP counter would fill up with everyone's
   failures. Read the real client IP from `X-Forwarded-For`, but only for requests coming from a
   trusted proxy — otherwise any client could choose its own IP. Only matters once the API is
   deployed behind one.
9. **Atomic attempt limits.** The login and sensitive-action limits read the counter before the
   attempt and increment it only after a failure, so requests sent in parallel all read a
   counter still under the threshold and all get through: 40 parallel logins gave 40 × 401 and
   no 429. An attacker gets up to ~100 tries per IP per window (the general limit's ceiling)
   instead of 5. Fix: reserve the attempt first with `INCR`, which is atomic in Redis, and decide
   on the value it returns, before checking the password. To decide when doing it: whether a
   successful attempt is decremented afterwards or simply counts.
