import time
import uuid

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.core.config import settings
from src.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from src.core.logging import setup_logging
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
)

# Enregistrement des routes de l'API avec préfixe de version (/api/v1)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(todos_router, prefix=settings.API_V1_STR)
app.include_router(categories_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)


logger = structlog.get_logger()
REQUEST_ID_HEADER = "X-Request-ID"


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
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
    structlog.contextvars.clear_contextvars()
    return response


@app.exception_handler(NotFoundError)
async def not_found_exception_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(ConflictError)
async def conflict_exception_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(ForbiddenError)
async def forbidden_exception_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": str(exc)},
    )


@app.exception_handler(UnauthorizedError)
async def unauthorized_exception_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": str(exc)},
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
