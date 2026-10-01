from hashlib import md5

import redis
from redis.asyncio import Redis

from src.core.config import settings

"""Client Redis, utilisé comme cache (catégories) et comme store des refresh tokens."""

redis_client: Redis = redis.asyncio.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis_client() -> Redis:
    """Dépendance FastAPI : renvoie le client Redis partagé, déjà créé au chargement du module."""
    return redis_client


def hash_redis_key(key: str) -> str:
    """Hash Redis Key."""
    return md5(key.encode()).hexdigest()
