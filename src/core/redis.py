import redis

from src.core.config import settings

"""Client Redis, utilisé comme cache (catégories) et, plus tard, comme store des refresh tokens."""

redis_client = redis.asyncio.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis_client():
    """Dépendance FastAPI : renvoie le client Redis partagé, déjà créé au chargement du module."""
    return redis_client
