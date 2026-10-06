"""Utilitaires d'idempotence : réservation, lecture et enregistrement des clés dans Redis."""

import hashlib
import json
from typing import Literal, NotRequired, TypedDict, cast

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.core.config import settings

logger = structlog.get_logger()


class IdempotencyRecord(TypedDict):
    status: Literal["in_progress", "done"]
    request_hash: str
    response_status: NotRequired[int]
    response_body: NotRequired[str]


def idempotency_redis_key(*, user_id: str, idempotency_key: str) -> str:
    """Redis key of one user's idempotency key."""
    return f"idempotency:{user_id}:{idempotency_key}"


def hash_request_body(body: bytes) -> str:
    """SHA-256 of the raw request body."""
    return hashlib.sha256(body).hexdigest()


async def claim_idempotency_key(redis_client: Redis, *, key: str, request_hash: str) -> bool:
    """SET NX an in_progress record with the short lock TTL; True if this request got it."""
    record: IdempotencyRecord = {"status": "in_progress", "request_hash": request_hash}
    is_claimed = await redis_client.set(
        key, json.dumps(record), ex=settings.IDEMPOTENCY_LOCK_TTL_SECONDS, nx=True
    )
    return bool(is_claimed)


async def get_idempotency_record(redis_client: Redis, key: str) -> IdempotencyRecord | None:
    """The stored record, or None if the key doesn't exist (anymore)."""
    if raw := await redis_client.get(key):
        return cast(IdempotencyRecord, json.loads(raw))


async def save_idempotent_response(
    redis_client: Redis, *, key: str, request_hash: str, response_status: int, response_body: str
) -> None:
    """Overwrite the claim with the final 2xx response, for IDEMPOTENCY_KEY_TTL_MINUTES."""
    record: IdempotencyRecord = {
        "status": "done",
        "request_hash": request_hash,
        "response_status": response_status,
        "response_body": response_body,
    }
    try:
        await redis_client.set(
            key, json.dumps(record), ex=60 * settings.IDEMPOTENCY_KEY_TTL_MINUTES
        )
    except RedisError:
        logger.warning("redis_unavailable", operation="save_idempotent_response", exc_info=True)


async def release_idempotency_key(redis_client: Redis, key: str) -> None:
    """Delete the claim so a retry runs for real."""
    try:
        await redis_client.delete(key)
    except RedisError:
        logger.warning("redis_unavailable", operation="release_idempotency_key", exc_info=True)
