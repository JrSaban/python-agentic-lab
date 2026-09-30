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
    mock_redis_client = AsyncMock()
    mock_category_repo.get_by_id.return_value = None

    service = CategoryService(repository=mock_category_repo, redis_client=mock_redis_client)

    with pytest.raises(NotFoundError):
        await service.get_category_or_404(1)

    mock_category_repo.get_by_id.assert_called_once_with(1)


async def test_get_category_or_404_returns_category_when_found():
    fake_category = Category(id=1, name="Test")
    mock_category_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_category_repo.get_by_id.return_value = fake_category

    service = CategoryService(repository=mock_category_repo, redis_client=mock_redis_client)

    result = await service.get_category_or_404(1)

    assert result == fake_category
    mock_category_repo.get_by_id.assert_called_once_with(1)


async def test_create_category(current_user: User):
    mock_category_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_redis_client.scan.return_value = (0, [])
    fake_category = Category(id=1, name="Test")
    mock_category_repo.create.return_value = fake_category

    service = CategoryService(repository=mock_category_repo, redis_client=mock_redis_client)
    data = CategoryCreate(name="Test")

    result = await service.create_category(created_by_id=current_user.id, data=data)

    assert result == fake_category
    mock_category_repo.create.assert_called_once_with(created_by_id=current_user.id, data=data)


async def test_create_duplicate_category_raises_conflict_error(current_user: User):
    mock_category_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_category_repo.create.side_effect = IntegrityError("stmt", {}, Exception("orig"))

    service = CategoryService(repository=mock_category_repo, redis_client=mock_redis_client)
    data = CategoryCreate(name="Sport")

    with pytest.raises(ConflictError):
        await service.create_category(created_by_id=current_user.id, data=data)


async def test_update_category_with_duplicate_name_raises_conflict_error(current_user: User):
    fake_category = Category(id=2, created_by_id=current_user.id, name="House")
    mock_category_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_category_repo.get_by_id.return_value = fake_category
    mock_category_repo.update.side_effect = IntegrityError("stmt", {}, Exception("orig"))

    service = CategoryService(repository=mock_category_repo, redis_client=mock_redis_client)
    data = CategoryUpdate(name="Sport")

    with pytest.raises(ConflictError):
        await service.update_category(user=current_user, entity_id=2, data=data)

    mock_category_repo.get_by_id.assert_called_once_with(2)


async def test_update_category_successfully(current_user: User):
    mock_category_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_redis_client.scan.return_value = (0, [])
    fake_category = Category(id=1, created_by_id=current_user.id, name="Sport")
    fake_category_updated = Category(id=1, created_by_id=current_user.id, name="House")

    mock_category_repo.get_by_id.return_value = fake_category
    mock_category_repo.update.return_value = fake_category_updated

    service = CategoryService(repository=mock_category_repo, redis_client=mock_redis_client)
    data = CategoryUpdate(name="House")

    result = await service.update_category(user=current_user, entity_id=1, data=data)

    assert result == fake_category_updated
    mock_category_repo.get_by_id.assert_called_once_with(1)
    mock_category_repo.update.assert_called_once_with(fake_category, data)


async def test_delete_category_by_admin_calls_repo_delete_when_found(current_admin_user: User):
    mock_category_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_redis_client.scan.return_value = (0, [])
    fake_category = Category(id=1, created_by_id=current_admin_user.id, name="Test")
    mock_category_repo.get_by_id.return_value = fake_category

    service = CategoryService(repository=mock_category_repo, redis_client=mock_redis_client)

    await service.delete_category(user=current_admin_user, entity_id=1)

    mock_category_repo.get_by_id.assert_called_once_with(1)
    mock_category_repo.delete.assert_called_once_with(fake_category)


async def test_update_category_by_non_owner_non_admin_raises_forbidden_error(current_user: User):
    fake_category = Category(id=1, created_by_id=current_user.id + 1, name="Sport")
    mock_category_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_category_repo.get_by_id.return_value = fake_category

    service = CategoryService(repository=mock_category_repo, redis_client=mock_redis_client)
    data = CategoryUpdate(name="House")

    with pytest.raises(ForbiddenError):
        await service.update_category(user=current_user, entity_id=1, data=data)

    mock_category_repo.get_by_id.assert_called_once_with(1)
    mock_category_repo.update.assert_not_called()


async def test_update_category_by_admin_on_others_category_success(current_admin_user: User):
    fake_category = Category(id=1, created_by_id=current_admin_user.id + 1, name="Sport")
    fake_category_updated = Category(id=1, created_by_id=current_admin_user.id + 1, name="House")
    mock_category_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_redis_client.scan.return_value = (0, [])
    mock_category_repo.get_by_id.return_value = fake_category
    mock_category_repo.update.return_value = fake_category_updated

    service = CategoryService(repository=mock_category_repo, redis_client=mock_redis_client)
    data = CategoryUpdate(name="House")

    result = await service.update_category(user=current_admin_user, entity_id=1, data=data)

    assert result == fake_category_updated
    mock_category_repo.update.assert_called_once_with(fake_category, data)


async def test_update_category_invalidates_item_cache(current_user: User):
    """update_category calls _invalidate_cache with the entity's own id — a regression
    test for the bug where a positional call bound entity_id to the wrong parameter
    and silently stopped invalidating the item cache."""
    ...


async def test_delete_category_invalidates_item_cache(current_admin_user: User):
    """Same regression test as above, for delete_category."""
    ...


async def test_list_categories_falls_back_to_db_when_redis_get_fails(current_user: User):
    """A RedisError on the cache read doesn't crash list_categories — it falls back
    to the repository, the same as a genuine cache miss."""
    ...


async def test_list_categories_falls_back_to_db_when_redis_set_fails(current_user: User):
    """A RedisError on the cache write after a DB fetch still returns the fresh data;
    it just doesn't get cached."""
    ...


async def test_list_categories_ignores_corrupted_cache_entry(current_user: User):
    """Malformed JSON (or a payload that no longer matches CategoryResponse) stored
    under the list cache key doesn't crash the request — it's treated like a cache miss."""
    ...


async def test_get_category_cached_falls_back_to_db_when_redis_unavailable(current_user: User):
    """A RedisError on get_category_cached's Redis calls doesn't prevent the category
    from being returned via the repository."""
    ...


async def test_invalidate_cache_does_not_raise_when_redis_unavailable(current_user: User):
    """update_category/delete_category still succeed even if the cache invalidation
    step (INCR / DELETE) raises a RedisError."""
    ...


async def test_delete_category_by_non_admin_raises_forbidden_error(current_user: User):
    mock_category_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    service = CategoryService(repository=mock_category_repo, redis_client=mock_redis_client)

    with pytest.raises(ForbiddenError):
        await service.delete_category(user=current_user, entity_id=1)

    mock_category_repo.get_by_id.assert_not_called()
    mock_category_repo.delete.assert_not_called()
