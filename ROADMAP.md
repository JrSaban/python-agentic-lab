# Roadmap

This project serves two learning goals at once: transferring backend skills from PHP/Laravel to
Python/FastAPI, and learning to work as an agentic developer — building software in deliberate
collaboration with AI agents and agent-facing tooling (MCP, evals, ...), not just using an
assistant to type faster.

Items are removed once done, as part of the same PR that finishes them. What's already built
lives in the README's Features section and in `CLAUDE.md`, not here.

1. **Rate limiting.** Redis-backed request throttling, the equivalent of Laravel's `throttle`
   middleware (FastAPI has nothing built in). Comes before MCP: the API should be hardened
   against an automated/looping consumer before one gets access to it.
2. **Idempotency keys.** An optional, client-generated `Idempotency-Key` header on write
   endpoints, so a retried request can't create a duplicate. Same reasoning as rate limiting —
   protect the API before exposing it to an agent that might retry blindly.
3. **ARQ.** An async, Redis-backed task queue for background jobs. Needs to exist before an MCP
   tool can trigger one.
4. **MCP.** Expose this API as an MCP server with a base set of tools (todos, categories), so an
   agent can act on it directly instead of through a human-facing REST client.
5. **Human-approval gate on an MCP write tool.** A tool that creates a pending change instead of
   applying it directly, requiring a human to approve it first. A small rehearsal of the
   human-validation pattern the next project (a support agent answering from documentation, with
   human approval before sending) will need for real.
6. **Audit log.** Who changed what, when, and whether it was a human or an agent — meaningful
   once there's more than one kind of actor writing to the API. Interacts with soft deletes.
7. **Evals for the MCP tools.** Not "does it work", but "does an agent actually use these tools
   correctly" — including the approval-gated one. Comes last, once the full tool surface exists.
