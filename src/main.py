from fastapi import FastAPI
from src.core.config import settings

"""
Point d'entrée principal de l'application.
Équivalent conceptuel de bootstrap/app.php + public/index.php dans Laravel.
"""

app = FastAPI(
    title=settings.APP_NAME,
    description="API REST moderne construite avec FastAPI et Clean Architecture",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI automatique
    redoc_url="/redoc",    # Documentation ReDoc alternative
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
