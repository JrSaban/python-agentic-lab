import time
import uuid

import jwt
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError

from src.core.config import settings
from src.core.exceptions import (
    AppBaseError,
)
from src.core.logging import setup_logging
from src.core.rate_limit import increment_rate_limit, seconds_until_reset
from src.core.redis import get_redis_client
from src.core.security import decode_access_token
from src.modules.auth.router import router as auth_router
from src.modules.categories.router import router as categories_router
from src.modules.todos.router import router as todos_router
from src.modules.users.router import router as users_router

"""
Point d'entrée principal de l'application.
Équivalent conceptuel de bootstrap/app.php + public/index.php dans Laravel.
"""


setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description="API REST moderne construite avec FastAPI et Clean Architecture",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# Enregistrement des routes de l'API avec préfixe de version (/api/v1)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(todos_router, prefix=settings.API_V1_STR)
app.include_router(categories_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)


logger = structlog.get_logger()
REQUEST_ID_HEADER = "X-Request-ID"


def _get_request_id(request: Request) -> str:
    """Extract request ID from header or generate a new one."""
    incoming = request.headers.get(REQUEST_ID_HEADER)
    if incoming and len(incoming) <= 64:
        return incoming
    return str(uuid.uuid4())


def _rate_limit_identity(request: Request) -> str:
    """User id from a valid access token, else the client IP."""
    if user_id := _user_id_from_token(request):
        return f"user:{user_id}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


def _user_id_from_token(request: Request) -> str | None:
    """Extract user ID from access token."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_access_token(auth_header.removeprefix("Bearer "))
        except jwt.PyJWTError:
            payload = {}
        if user_id := payload.get("sub"):
            return user_id
    return None


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    key = f"rate_limit:general:{_rate_limit_identity(request)}"

    try:
        attempts = await increment_rate_limit(
            get_redis_client(), [key], settings.GENERAL_RATE_LIMIT_WINDOW_MINUTES
        )
        if attempts[key] > settings.GENERAL_RATE_LIMIT_MAX_REQUESTS:
            retry_after = await seconds_until_reset(get_redis_client(), key)
            return JSONResponse(
                status_code=429,
                content={"detail": "Trop de requêtes, veuillez réessayer plus tard."},
                headers={"Retry-After": str(retry_after)},
            )
    except RedisError:
        logger.warning("redis_unavailable", operation="rate_limit_middleware", exc_info=True)

    return await call_next(request)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    structlog.contextvars.clear_contextvars()
    request_id = _get_request_id(request)
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    response.headers[REQUEST_ID_HEADER] = request_id
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 1),
    )
    return response


@app.exception_handler(AppBaseError)
async def app_error_handler(request: Request, exc: AppBaseError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc)},
        headers=exc.headers,
    )


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, str]:
    """
    Endpoint de vérification de l'état de l'API.
    Utilisé par Docker / Kubernetes / Load Balancer pour les healthchecks.
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
    }
