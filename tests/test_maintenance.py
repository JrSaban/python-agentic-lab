"""Tests d'intégration du job de pruning des lignes soft-deletées."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.modules.categories.models import Category
from src.modules.categories.repository import CategoryRepository
from src.modules.categories.schemas import CategoryCreate
from src.modules.maintenance.tasks import prune_soft_deleted
from src.modules.todos.models import Todo
from src.modules.todos.repository import TodoRepository
from src.modules.todos.schemas import TodoCreate
from src.modules.todos_categories.models import todos_categories
from src.modules.users.models import User
from tests.conftest import test_session_factory as session_factory

PAST_RETENTION = timedelta(days=settings.SOFT_DELETE_RETENTION_DAYS + 1)
WITHIN_RETENTION = timedelta(days=settings.SOFT_DELETE_RETENTION_DAYS - 1)


@pytest.fixture(autouse=True)
def job_uses_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """The job opens its own session from the production factory, out of reach of
    dependency_overrides: point it at the test database instead."""
    monkeypatch.setattr("src.modules.maintenance.tasks.async_session_factory", session_factory)


async def _run_job() -> dict[str, int]:
    """Send the job; the in-memory test broker runs it immediately."""
    task = await prune_soft_deleted.kiq()
    result = await task.wait_result()
    assert not result.is_err, result.error
    return result.return_value


async def _soft_delete(session: AsyncSession, entity: Todo | Category, ago: timedelta) -> None:
    entity.deleted_at = datetime.now(UTC) - ago
    await session.flush()


async def _remaining_ids(session: AsyncSession, model: type[Todo] | type[Category]) -> set[int]:
    """Every id still in the table, soft-deleted or not (the repositories hide those)."""
    result = await session.execute(select(model.id))
    return set(result.scalars())


async def test_prunes_only_rows_soft_deleted_beyond_retention(
    db_session: AsyncSession, current_user: User
) -> None:
    """Rows soft-deleted longer ago than SOFT_DELETE_RETENTION_DAYS are deleted for good;
    recently soft-deleted and live rows stay. The job reports what it deleted."""
    todos = TodoRepository(db_session)
    categories = CategoryRepository(db_session)
    old_todo = await todos.create(current_user.id, TodoCreate(title="Old"), [])
    recent_todo = await todos.create(current_user.id, TodoCreate(title="Recent"), [])
    live_todo = await todos.create(current_user.id, TodoCreate(title="Live"), [])
    old_category = await categories.create(current_user.id, CategoryCreate(name="Old"))
    recent_category = await categories.create(current_user.id, CategoryCreate(name="Recent"))
    live_category = await categories.create(current_user.id, CategoryCreate(name="Live"))
    await _soft_delete(db_session, old_todo, PAST_RETENTION)
    await _soft_delete(db_session, recent_todo, WITHIN_RETENTION)
    await _soft_delete(db_session, old_category, PAST_RETENTION)
    await _soft_delete(db_session, recent_category, WITHIN_RETENTION)
    await db_session.commit()

    assert await _run_job() == {"todos": 1, "categories": 1}

    async with session_factory() as session:
        assert await _remaining_ids(session, Todo) == {recent_todo.id, live_todo.id}
        assert await _remaining_ids(session, Category) == {recent_category.id, live_category.id}


async def test_pruning_removes_association_rows(
    db_session: AsyncSession, current_user: User
) -> None:
    """The todos_categories rows of a pruned todo or category go with it (ON DELETE
    CASCADE), so no association is left pointing at a row that no longer exists."""
    categories = CategoryRepository(db_session)
    todos = TodoRepository(db_session)
    old_category = await categories.create(current_user.id, CategoryCreate(name="Old"))
    live_category = await categories.create(current_user.id, CategoryCreate(name="Live"))
    # A live todo linked to a pruned category, and a pruned todo linked to a live category.
    live_todo = await todos.create(current_user.id, TodoCreate(title="Live"), [old_category])
    old_todo = await todos.create(current_user.id, TodoCreate(title="Old"), [live_category])
    await _soft_delete(db_session, old_category, PAST_RETENTION)
    await _soft_delete(db_session, old_todo, PAST_RETENTION)
    await db_session.commit()

    await _run_job()

    async with session_factory() as session:
        result = await session.execute(select(todos_categories))
        assert result.all() == []
        assert live_todo.id in await _remaining_ids(session, Todo)


async def test_nothing_to_prune_reports_zero(db_session: AsyncSession, current_user: User) -> None:
    """With no row past retention, the job deletes nothing and says so."""
    await TodoRepository(db_session).create(current_user.id, TodoCreate(title="Live"), [])
    await db_session.commit()

    assert await _run_job() == {"todos": 0, "categories": 0}


def test_job_is_scheduled_weekly() -> None:
    """The scheduler reads this label: Sunday 03:00 UTC, once a week."""
    assert prune_soft_deleted.labels["schedule"] == [{"cron": "0 3 * * 0"}]
