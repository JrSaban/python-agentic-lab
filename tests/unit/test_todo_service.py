from unittest.mock import AsyncMock

import pytest

from src.core.exceptions import NotFoundError
from src.modules.todos.models import Todo
from src.modules.todos.schemas import TodoCreate, TodoUpdate
from src.modules.todos.service import TodoService


async def test_get_todo_or_404_raises_when_not_found():
    mock_todo_repo = AsyncMock()
    mock_todo_repo.get_by_id.return_value = None

    service = TodoService(repository=mock_todo_repo, category_repository=AsyncMock())

    with pytest.raises(NotFoundError):
        await service.get_todo_or_404(1)

    mock_todo_repo.get_by_id.assert_called_once_with(1, with_categories=False)


async def test_get_todo_or_404_returns_todo_when_found():
    fake_todo = Todo(id=1, title="Test")
    mock_todo_repo = AsyncMock()
    mock_todo_repo.get_by_id.return_value = fake_todo

    service = TodoService(repository=mock_todo_repo, category_repository=AsyncMock())

    result = await service.get_todo_or_404(1)

    assert result == fake_todo
    mock_todo_repo.get_by_id.assert_called_once_with(1, with_categories=False)


async def test_create_todo_resolves_categories():
    mock_todo_repo = AsyncMock()
    mock_category_repo = AsyncMock()
    mock_category_repo.get_by_ids.return_value = ["cat1", "cat2"]

    service = TodoService(repository=mock_todo_repo, category_repository=mock_category_repo)
    data = TodoCreate(title="Test", category_ids=[1, 2])

    await service.create_todo(data)

    mock_todo_repo.create.assert_called_once_with(data, ["cat1", "cat2"])


async def test_update_todo_resolves_categories():
    mock_todo_repo = AsyncMock()
    mock_category_repo = AsyncMock()
    mock_category_repo.get_by_ids.return_value = ["cat1", "cat2"]
    fake_todo = Todo(id=1, title="Test")
    mock_todo_repo.get_by_id.return_value = fake_todo
    mock_todo_repo.update.return_value = fake_todo

    service = TodoService(repository=mock_todo_repo, category_repository=mock_category_repo)
    data = TodoUpdate(title="Test", category_ids=[1, 2])

    result = await service.update_todo(1, data)

    assert result == fake_todo
    mock_todo_repo.get_by_id.assert_called_once_with(1, with_categories=True)
    mock_category_repo.get_by_ids.assert_called_once_with([1, 2])
    mock_todo_repo.update.assert_called_once_with(fake_todo, data, ["cat1", "cat2"])


async def test_update_todo_without_categories():
    mock_todo_repo = AsyncMock()
    mock_category_repo = AsyncMock()
    fake_todo = Todo(id=1, title="Test")
    mock_todo_repo.get_by_id.return_value = fake_todo
    mock_todo_repo.update.return_value = fake_todo

    service = TodoService(repository=mock_todo_repo, category_repository=mock_category_repo)
    data = TodoUpdate(title="Test")

    result = await service.update_todo(1, data)

    assert result == fake_todo
    mock_todo_repo.get_by_id.assert_called_once_with(1, with_categories=False)
    mock_category_repo.get_by_ids.assert_not_called()
    mock_todo_repo.update.assert_called_once_with(fake_todo, data, None)


async def test_delete_todo_calls_repo_delete_when_found():
    mock_todo_repo = AsyncMock()
    fake_todo = Todo(id=1, title="Test")
    mock_todo_repo.get_by_id.return_value = fake_todo

    service = TodoService(repository=mock_todo_repo, category_repository=AsyncMock())

    await service.delete_todo(1)

    mock_todo_repo.get_by_id.assert_called_once_with(1, with_categories=False)
    mock_todo_repo.delete.assert_called_once_with(fake_todo)
