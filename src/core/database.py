from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.core.config import settings

r"""
Point d'accès aux données (SQLAlchemy 2.0 Async).
Équivalent conceptuel de config/database.php + Illuminate\Database\Eloquent\Model dans Laravel.
"""

# 1. Le Moteur (Engine) : Gère le pool de connexions asynchrones vers PostgreSQL
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,  # Affiche les requêtes SQL générées dans les logs si DEBUG=True
    future=True,
    pool_pre_ping=True,  # Vérifie la santé de la connexion avant chaque requête
)

# 2. La Fabrique de Sessions (SessionMaker) : Instancie une AsyncSession pour chaque transaction
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,  # Évite les re-requêtes inutiles après un commit
)


# 3. La Classe de Base Déclarative : Tous les modèles (tables) hériteront de cette classe
class Base(AsyncAttrs, DeclarativeBase):
    """Classe de base dont héritent tous les modèles SQLAlchemy du projet."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)


# 4. Dépendance FastAPI pour injecter la session BDD par requête
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Gestionnaire de cycle de vie d'une transaction BDD par requête HTTP.
    - Ouvre la session au début du traitement de la route
    - Commit automatiquement si aucune exception n'est levée
    - Rollback automatiquement en cas d'erreur
    - Ferme toujours la connexion (libération du pool)
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
