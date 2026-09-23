import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

"""
Configuration globale des tests avec pytest (conftest.py).
Équivalent conceptuel de tests/TestCase.php avec RefreshDatabase dans Laravel.
"""

# Doit être fixé avant TOUT import de src.* : Settings() (instancié au chargement de
# src.core.config, importé transitivement par la plupart des modules de src) lit la
# variable d'environnement DEBUG dès sa construction, et setup_logging() (dans
# src.main) s'en sert pour choisir le niveau du root logger.
os.environ.setdefault("DEBUG", "False")
os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production-123456789012"

from src.core.database import Base, get_db_session  # noqa: E402
from src.core.security import hash_password  # noqa: E402
from src.main import app  # noqa: E402
from src.modules.auth.router import get_current_user  # noqa: E402
from src.modules.users.models import User  # noqa: E402
from src.modules.users.repository import UserRepository  # noqa: E402
from src.modules.users.schemas import UserCreate  # noqa: E402

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


@pytest.fixture
async def current_user(db_session: AsyncSession) -> User:
    """Crée un utilisateur normal directement en base (sans passer par l'API)."""
    repository = UserRepository(db_session)
    return await repository.create(
        UserCreate(
            email="user@test.com",
            first_name="Test",
            last_name="User",
            password="secret123",
            confirm_password="secret123",
        ),
        hash_password("secret123"),
    )


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Crée un second utilisateur normal directement en base, pour tester l'isolation
    entre utilisateurs (aucun client authentifié n'est fourni pour lui : on ne
    l'utilise que comme propriétaire de données créées via un repository)."""
    repository = UserRepository(db_session)
    return await repository.create(
        UserCreate(
            email="other@test.com",
            first_name="Other",
            last_name="User",
            password="secret123",
            confirm_password="secret123",
        ),
        hash_password("secret123"),
    )


@pytest.fixture
async def authenticated_client(client: AsyncClient, current_user: User) -> AsyncClient:
    """Le client de test, mais avec get_current_user déjà surchargé par current_user."""
    app.dependency_overrides[get_current_user] = lambda: current_user
    return client


@pytest.fixture
async def current_admin_user(db_session: AsyncSession) -> User:
    """Crée un utilisateur admin directement en base (sans passer par l'API)."""
    repository = UserRepository(db_session)
    admin_user = await repository.create(
        UserCreate(
            email="admin@test.com",
            first_name="Test",
            last_name="User",
            password="secret123",
            confirm_password="secret123",
        ),
        hash_password("secret123"),
    )
    return await repository.set_admin(admin_user, True)


@pytest.fixture
async def authenticated_admin(client: AsyncClient, current_admin_user: User) -> AsyncClient:
    """Le client de test, mais avec get_current_user déjà surchargé par current_admin_user."""
    app.dependency_overrides[get_current_user] = lambda: current_admin_user
    return client
