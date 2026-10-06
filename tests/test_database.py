"""Tests d'intégration du cycle de vie de la session BDD (get_db_session)."""

from collections.abc import AsyncGenerator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.main import app


async def test_failed_commit_returns_500_not_success(
    authenticated_client: AsyncClient, db_session: AsyncSession
) -> None:
    """The commit runs before the response is sent (scope="function"): if it fails,
    the client gets a 500, never a 201 for a row that was rolled back."""

    async def session_with_failing_commit() -> AsyncGenerator[AsyncSession, None]:
        yield db_session
        raise RuntimeError("commit failed")

    app.dependency_overrides[get_db_session] = session_with_failing_commit

    # raise_app_exceptions=False: get the 500 response instead of the exception itself,
    # since the status code is what tells the two behaviours apart.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/todos", json={"title": "Never committed"})

    assert response.status_code == 500
