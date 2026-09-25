from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from src.modules.categories.models import Category
from src.modules.categories.schemas import CategoryCreate, CategoryUpdate
from src.modules.categories.service import CategoryService
from src.modules.users.models import User


async def test_get_category_or_404_raises_when_not_found():
    mock_category_repo = AsyncMock()
    mock_category_repo.get_by_id.return_value = None

    service = CategoryService(repository=mock_category_repo)

    with pytest.raises(NotFoundError):
        await service.get_category_or_404(1)

    mock_category_repo.get_by_id.assert_called_once_with(1)


async def test_get_category_or_404_returns_category_when_found():
    fake_category = Category(id=1, name="Test")
    mock_category_repo = AsyncMock()
    mock_category_repo.get_by_id.return_value = fake_category

    service = CategoryService(repository=mock_category_repo)

    result = await service.get_category_or_404(1)

    assert result == fake_category
    mock_category_repo.get_by_id.assert_called_once_with(1)


async def test_create_category(current_user: User):
    mock_category_repo = AsyncMock()
    fake_category = Category(id=1, name="Test")
    mock_category_repo.create.return_value = fake_category

    service = CategoryService(repository=mock_category_repo)
    data = CategoryCreate(name="Test")

    result = await service.create_category(created_by_id=current_user.id, data=data)

    assert result == fake_category
    mock_category_repo.create.assert_called_once_with(created_by_id=current_user.id, data=data)


async def test_create_duplicate_category_raises_conflict_error(current_user: User):
    mock_category_repo = AsyncMock()
    mock_category_repo.create.side_effect = IntegrityError("stmt", {}, Exception("orig"))

    service = CategoryService(repository=mock_category_repo)
    data = CategoryCreate(name="Sport")

    with pytest.raises(ConflictError):
        await service.create_category(created_by_id=current_user.id, data=data)


async def test_update_category_with_duplicate_name_raises_conflict_error(current_user: User):
    fake_category = Category(id=2, created_by_id=current_user.id, name="House")
    mock_category_repo = AsyncMock()
    mock_category_repo.get_by_id.return_value = fake_category
    mock_category_repo.update.side_effect = IntegrityError("stmt", {}, Exception("orig"))

    service = CategoryService(repository=mock_category_repo)
    data = CategoryUpdate(name="Sport")

    with pytest.raises(ConflictError):
        await service.update_category(user=current_user, entity_id=2, data=data)

    mock_category_repo.get_by_id.assert_called_once_with(2)


async def test_update_category_successfully(current_user: User):
    mock_category_repo = AsyncMock()
    fake_category = Category(id=1, created_by_id=current_user.id, name="Sport")
    fake_category_updated = Category(id=1, created_by_id=current_user.id, name="House")

    mock_category_repo.get_by_id.return_value = fake_category
    mock_category_repo.update.return_value = fake_category_updated

    service = CategoryService(repository=mock_category_repo)
    data = CategoryUpdate(name="House")

    result = await service.update_category(user=current_user, entity_id=1, data=data)

    assert result == fake_category_updated
    mock_category_repo.get_by_id.assert_called_once_with(1)
    mock_category_repo.update.assert_called_once_with(fake_category, data)


async def test_delete_category_by_admin_calls_repo_delete_when_found(current_admin_user: User):
    mock_category_repo = AsyncMock()
    fake_category = Category(id=1, created_by_id=current_admin_user.id, name="Test")
    mock_category_repo.get_by_id.return_value = fake_category

    service = CategoryService(repository=mock_category_repo)

    await service.delete_category(user=current_admin_user, entity_id=1)

    mock_category_repo.get_by_id.assert_called_once_with(1)
    mock_category_repo.delete.assert_called_once_with(fake_category)


async def test_update_category_by_non_owner_non_admin_raises_forbidden_error(current_user: User):
    fake_category = Category(id=1, created_by_id=current_user.id + 1, name="Sport")
    mock_category_repo = AsyncMock()
    mock_category_repo.get_by_id.return_value = fake_category

    service = CategoryService(repository=mock_category_repo)
    data = CategoryUpdate(name="House")

    with pytest.raises(ForbiddenError):
        await service.update_category(user=current_user, entity_id=1, data=data)

    mock_category_repo.get_by_id.assert_called_once_with(1)
    mock_category_repo.update.assert_not_called()


async def test_update_category_by_admin_on_others_category_success(current_admin_user: User):
    fake_category = Category(id=1, created_by_id=current_admin_user.id + 1, name="Sport")
    fake_category_updated = Category(id=1, created_by_id=current_admin_user.id + 1, name="House")
    mock_category_repo = AsyncMock()
    mock_category_repo.get_by_id.return_value = fake_category
    mock_category_repo.update.return_value = fake_category_updated

    service = CategoryService(repository=mock_category_repo)
    data = CategoryUpdate(name="House")

    result = await service.update_category(user=current_admin_user, entity_id=1, data=data)

    assert result == fake_category_updated
    mock_category_repo.update.assert_called_once_with(fake_category, data)


async def test_delete_category_by_non_admin_raises_forbidden_error(current_user: User):
    mock_category_repo = AsyncMock()

    service = CategoryService(repository=mock_category_repo)

    with pytest.raises(ForbiddenError):
        await service.delete_category(user=current_user, entity_id=1)

    mock_category_repo.get_by_id.assert_not_called()
    mock_category_repo.delete.assert_not_called()
