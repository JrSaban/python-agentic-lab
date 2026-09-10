from unittest.mock import AsyncMock

import pytest

from src.core.exceptions import ConflictError, NotFoundError
from src.modules.categories.models import Category
from src.modules.categories.schemas import CategoryCreate, CategoryUpdate
from src.modules.categories.service import CategoryService


async def test_get_category_or_404_raises_when_not_found():
    mock_category_repo = AsyncMock()
    mock_category_repo.get_by_id.return_value = None

    service = CategoryService(repository=mock_category_repo)

    with pytest.raises(NotFoundError):
        await service.get_category_or_404(1)

    mock_category_repo.get_by_id.assert_called_once_with(1, with_todos=False)


async def test_get_category_or_404_returns_category_when_found():
    fake_category = Category(id=1, name="Test")
    mock_category_repo = AsyncMock()
    mock_category_repo.get_by_id.return_value = fake_category

    service = CategoryService(repository=mock_category_repo)

    result = await service.get_category_or_404(1)

    assert result == fake_category
    mock_category_repo.get_by_id.assert_called_once_with(1, with_todos=False)


async def test_create_category():
    mock_category_repo = AsyncMock()
    fake_category = Category(id=1, name="Test")
    mock_category_repo.get_by_name.return_value = None
    mock_category_repo.create.return_value = fake_category

    service = CategoryService(repository=mock_category_repo)
    data = CategoryCreate(name="Test")

    result = await service.create_category(data)

    assert result == fake_category
    mock_category_repo.get_by_name.assert_called_once_with("Test")
    mock_category_repo.create.assert_called_once_with(data)


async def test_create_duplicate_category_raises_conflict_error():
    fake_category = Category(id=1, name="Sport")
    mock_category_repo = AsyncMock()
    mock_category_repo.get_by_name.return_value = fake_category

    service = CategoryService(repository=mock_category_repo)
    data = CategoryCreate(name="Sport")

    with pytest.raises(ConflictError):
        await service.create_category(data)

    mock_category_repo.get_by_name.assert_called_once_with("Sport")


async def test_update_category_with_same_name_does_not_raise_conflict_error():
    fake_category = Category(id=1, name="Sport")
    fake_category_updated = Category(id=1, name="sport")
    mock_category_repo = AsyncMock()
    mock_category_repo.get_by_id.return_value = fake_category
    mock_category_repo.update.return_value = fake_category_updated

    service = CategoryService(repository=mock_category_repo)
    data = CategoryUpdate(name="sport")

    result = await service.update_category(1, data)

    assert result == fake_category_updated
    mock_category_repo.get_by_id.assert_called_once_with(1, with_todos=False)
    mock_category_repo.get_by_name.assert_not_called()
    mock_category_repo.update.assert_called_once_with(fake_category, data)


async def test_update_category_without_name_does_not_call_get_by_name():
    fake_category = Category(id=1, name="Sport", color="#ff0000")
    fake_category_updated = Category(id=1, name="Sport", color="#0000ff")
    mock_category_repo = AsyncMock()
    mock_category_repo.get_by_id.return_value = fake_category
    mock_category_repo.update.return_value = fake_category_updated

    service = CategoryService(repository=mock_category_repo)
    data = CategoryUpdate(color="#0000ff")

    result = await service.update_category(1, data)

    assert result == fake_category_updated
    mock_category_repo.get_by_id.assert_called_once_with(1, with_todos=False)
    mock_category_repo.get_by_name.assert_not_called()
    mock_category_repo.update.assert_called_once_with(fake_category, data)


async def test_update_category_with_duplicate_name_raises_conflict_error():
    fake_category = Category(id=1, name="Sport")
    fake_category_2 = Category(id=2, name="House")
    mock_category_repo = AsyncMock()
    mock_category_repo.get_by_id.return_value = fake_category_2
    mock_category_repo.get_by_name.return_value = fake_category

    service = CategoryService(repository=mock_category_repo)
    data = CategoryUpdate(name="Sport")

    with pytest.raises(ConflictError):
        await service.update_category(2, data)

    mock_category_repo.get_by_id.assert_called_once_with(2, with_todos=False)
    mock_category_repo.get_by_name.assert_called_once_with("Sport")


async def test_update_category_successfully():
    mock_category_repo = AsyncMock()
    fake_category = Category(id=1, name="Sport")
    fake_category_updated = Category(id=1, name="House")

    mock_category_repo.get_by_id.return_value = fake_category
    mock_category_repo.get_by_name.return_value = None
    mock_category_repo.update.return_value = fake_category_updated

    service = CategoryService(repository=mock_category_repo)
    data = CategoryUpdate(name="House")

    result = await service.update_category(1, data)

    assert result == fake_category_updated
    mock_category_repo.get_by_id.assert_called_once_with(1, with_todos=False)
    mock_category_repo.get_by_name.assert_called_once_with("House")
    mock_category_repo.update.assert_called_once_with(fake_category, data)


async def test_delete_category_calls_repo_delete_when_found():
    mock_category_repo = AsyncMock()
    fake_category = Category(id=1, name="Test")
    mock_category_repo.get_by_id.return_value = fake_category

    service = CategoryService(repository=mock_category_repo)

    await service.delete_category(1)

    mock_category_repo.get_by_id.assert_called_once_with(1, with_todos=False)
    mock_category_repo.delete.assert_called_once_with(fake_category)
