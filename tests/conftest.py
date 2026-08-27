from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.database import Base, get_db_session
from src.main import app

"""
Configuration globale des tests avec pytest (conftest.py).
Équivalent conceptuel de tests/TestCase.php avec RefreshDatabase dans Laravel.
"""

# Base de données SQLite en mémoire vive (ultra-rapide, isolée par session de test)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

test_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(autouse=True)
async def setup_test_database() -> AsyncGenerator[None, None]:
    """
    Fixture automatique (autouse=True) :
    - Avant chaque test : crée toutes les tables vierges.
    - Après chaque test : supprime toutes les tables pour garantir une isolation totale.
    Équivalent de RefreshDatabase dans Laravel.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield  # Le test s'exécute ici

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fournit une session BDD de test active si un test en a besoin directement."""
    async with test_session_factory() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Client HTTP asynchrone (httpx.AsyncClient).
    Interroge l'application FastAPI en mémoire (sans ouvrir de vrai port réseau).
    Surcharge la dépendance de production 'get_db_session' par notre session de test.
    """

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    # Surcharge la dépendance de FastAPI
    app.dependency_overrides[get_db_session] = override_get_db_session

    # Crée le client de test
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client

    # Nettoyage : rétablit la configuration d'origine
    app.dependency_overrides.clear()
