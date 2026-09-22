"""Tests d'intégration des endpoints Categories."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.categories.repository import CategoryRepository
from src.modules.categories.schemas import CategoryCreate
from src.modules.todos.repository import TodoRepository
from src.modules.todos.schemas import TodoCreate
from src.modules.users.models import User


async def test_create_category_success(authenticated_client: AsyncClient) -> None:
    """Successful category creation (POST /api/v1/categories)."""
    payload = {
        "name": "Sport",
    }
    response = await authenticated_client.post("/api/v1/categories", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == payload["name"]
    assert data["color"] == "#FAFAFA"
    assert "created_at" in data


async def test_create_category_missing_name_returns_422(authenticated_client: AsyncClient) -> None:
    """Omitting the name is rejected by Pydantic (422 Unprocessable Entity)."""
    response = await authenticated_client.post("/api/v1/categories", json={"color": "#FF0000"})
    assert response.status_code == 422


async def test_create_category_empty_name_returns_422(authenticated_client: AsyncClient) -> None:
    """An empty name ("") is rejected thanks to min_length=1."""
    response = await authenticated_client.post(
        "/api/v1/categories", json={"name": "", "color": "#FF0000"}
    )
    assert response.status_code == 422


async def test_create_category_empty_color_returns_422(authenticated_client: AsyncClient) -> None:
    """An empty color ("") is rejected thanks to the regex pattern."""
    response = await authenticated_client.post(
        "/api/v1/categories", json={"name": "Test", "color": ""}
    )
    assert response.status_code == 422


async def test_list_categories(authenticated_client: AsyncClient) -> None:
    """Fetching the list of categories (GET /api/v1/categories)."""
    # 1. Création de deux catégories
    await authenticated_client.post("/api/v1/categories", json={"name": "Sport"})
    await authenticated_client.post(
        "/api/v1/categories", json={"name": "House", "color": "#00FF00"}
    )

    # 2. Récupération de la liste
    response = await authenticated_client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["items"][0]["name"] == "House"  # Tri croissant par nom


async def test_get_category_by_id_success(authenticated_client: AsyncClient) -> None:
    """Fetching a category by its ID (GET /api/v1/categories/{id})."""
    create_res = await authenticated_client.post(
        "/api/v1/categories", json={"name": "Sport", "color": "#FF0000"}
    )
    created_id = create_res.json()["id"]

    response = await authenticated_client.get(f"/api/v1/categories/{created_id}")
    assert response.status_code == 200
    assert response.json()["id"] == created_id
    assert response.json()["name"] == "Sport"
    assert response.json()["color"] == "#FF0000"


async def test_get_category_not_found_returns_404(authenticated_client: AsyncClient) -> None:
    """A nonexistent ID returns 404 Not Found."""
    response = await authenticated_client.get("/api/v1/categories/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Catégorie avec l'ID 99999 introuvable."


async def test_patch_category_success(authenticated_client: AsyncClient) -> None:
    """Partial update by its creator (PATCH /api/v1/categories/{id})."""
    create_res = await authenticated_client.post(
        "/api/v1/categories", json={"name": "Sport", "color": "#FF0000"}
    )
    category_id = create_res.json()["id"]

    # On ne modifie QUE name
    update_res = await authenticated_client.patch(
        f"/api/v1/categories/{category_id}", json={"name": "House"}
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["name"] == "House"
    assert data["color"] == "#FF0000"  # La couleur n'a pas été effacée !


async def test_patch_category_by_admin_success(
    authenticated_admin: AsyncClient, other_user: User, db_session: AsyncSession
) -> None:
    """An admin can partially update a category they didn't create."""
    cat_1 = await CategoryRepository(db_session).create(
        created_by_id=other_user.id, data=CategoryCreate(name="Sport")
    )

    update_res = await authenticated_admin.patch(
        f"/api/v1/categories/{cat_1.id}", json={"name": "House"}
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["name"] == "House"


async def test_patch_category_by_non_admin_not_owner_returns_403(
    authenticated_client: AsyncClient, other_user: User, db_session: AsyncSession
) -> None:
    """A non-admin, non-owner user updating a category → 403."""
    cat_1 = await CategoryRepository(db_session).create(
        created_by_id=other_user.id, data=CategoryCreate(name="Sport")
    )

    update_res = await authenticated_client.patch(
        f"/api/v1/categories/{cat_1.id}", json={"name": "House"}
    )
    assert update_res.status_code == 403


async def test_patch_category_with_null_name_returns_422(authenticated_client: AsyncClient) -> None:
    """If the client explicitly sends name=null, Pydantic returns a 422."""
    create_res = await authenticated_client.post("/api/v1/categories", json={"name": "Sport"})
    category_id = create_res.json()["id"]

    response = await authenticated_client.patch(
        f"/api/v1/categories/{category_id}", json={"name": None}
    )
    assert response.status_code == 422


async def test_delete_category_by_admin_success(
    authenticated_admin: AsyncClient, other_user: User, db_session: AsyncSession
) -> None:
    """An admin can delete a category they didn't create (DELETE /api/v1/categories/{id})."""
    cat_1 = await CategoryRepository(db_session).create(
        created_by_id=other_user.id, data=CategoryCreate(name="Sport")
    )

    # 1. Suppression
    del_res = await authenticated_admin.delete(f"/api/v1/categories/{cat_1.id}")
    assert del_res.status_code == 204

    # 2. Vérification que la catégorie n'existe plus
    get_res = await authenticated_admin.get(f"/api/v1/categories/{cat_1.id}")
    assert get_res.status_code == 404


async def test_delete_category_by_non_admin_returns_403(authenticated_client: AsyncClient) -> None:
    """A non-admin user deleting a category (even their own) → 403."""
    cat_1 = await authenticated_client.post("/api/v1/categories", json={"name": "Sport"})

    del_res = await authenticated_client.delete(f"/api/v1/categories/{cat_1.json()["id"]}")
    assert del_res.status_code == 403


async def test_create_category_duplicate_name_returns_409(
    authenticated_client: AsyncClient,
) -> None:
    """A category with the same name is rejected (409 Conflict)."""
    # 1. Création de la catégorie
    await authenticated_client.post("/api/v1/categories", json={"name": "Sport"})

    # 2. Tentative de création de la même catégorie
    response = await authenticated_client.post("/api/v1/categories", json={"name": "Sport"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Une catégorie avec le nom Sport existe déjà."


async def test_create_category_case_insensitive_duplicate_returns_409(
    authenticated_client: AsyncClient,
) -> None:
    """A duplicate name in uppercase is also rejected (409 Conflict)."""
    # 1. Création de la catégorie en minuscules
    await authenticated_client.post("/api/v1/categories", json={"name": "Sport"})

    # 2. Tentative de création de la même catégorie en majuscules
    response = await authenticated_client.post("/api/v1/categories", json={"name": "SPORT"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Une catégorie avec le nom SPORT existe déjà."


async def test_create_category_uppercases_color(authenticated_client: AsyncClient) -> None:
    """The color field is uppercased."""
    create_res = await authenticated_client.post(
        "/api/v1/categories", json={"name": "Sport", "color": "#fbfbfb"}
    )
    category_id = create_res.json()["id"]

    category = await authenticated_client.get(f"/api/v1/categories/{category_id}")
    assert category.status_code == 200
    assert category.json()["id"] == category_id
    assert category.json()["name"] == "Sport"
    assert category.json()["color"] == "#FBFBFB"


async def test_update_category_name_conflict_returns_409(authenticated_client: AsyncClient) -> None:
    """Renaming a category to another existing category's name returns 409."""
    # 1. Création de deux catégories
    await authenticated_client.post("/api/v1/categories", json={"name": "House"})
    create_res = await authenticated_client.post("/api/v1/categories", json={"name": "Sport"})
    category_id = create_res.json()["id"]

    # 2. Tentative de renommer la catégorie "Sport" en "house"
    response = await authenticated_client.patch(
        f"/api/v1/categories/{category_id}", json={"name": "house"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Une catégorie avec le nom house existe déjà."


async def test_update_category_keep_same_name_succeeds(authenticated_client: AsyncClient) -> None:
    """Renaming a category to its own current name doesn't trigger a 409 Conflict."""
    # 1. Création de la catégorie
    create_res = await authenticated_client.post("/api/v1/categories", json={"name": "sport"})
    category_id = create_res.json()["id"]

    # 2. Tentative de renommer la catégorie "sport" en "Sport"
    response = await authenticated_client.patch(
        f"/api/v1/categories/{category_id}", json={"name": "Sport"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == category_id
    assert response.json()["name"] == "Sport"


async def test_get_todos_by_category(
    authenticated_client: AsyncClient, other_user: User, db_session: AsyncSession
) -> None:
    """Fetching the todos associated with a category."""
    cat_1 = await authenticated_client.post("/api/v1/categories", json={"name": "Sport"})
    cat_1_id = cat_1.json()["id"]
    category = await CategoryRepository(session=db_session).get_by_id(cat_1_id)
    assert category is not None

    await TodoRepository(session=db_session).create(
        owner_id=other_user.id, data=TodoCreate(title="Tache other user"), categories=[category]
    )

    todo_1 = await authenticated_client.post(
        "/api/v1/todos", json={"title": "Tache 1", "category_ids": [cat_1_id]}
    )
    todo_2 = await authenticated_client.post(
        "/api/v1/todos", json={"title": "Tache 2", "category_ids": [cat_1_id]}
    )

    # 2. Récupération des tâches de la catégorie
    response = await authenticated_client.get(f"/api/v1/categories/{cat_1_id}/todos")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["items"][0]["id"] == todo_2.json()["id"]
    assert data["items"][1]["id"] == todo_1.json()["id"]


async def test_get_todos_by_category_as_admin(
    authenticated_admin: AsyncClient, other_user: User, db_session: AsyncSession
) -> None:
    """An admin fetching a category's todos sees every user's todos."""
    cat_1 = await authenticated_admin.post("/api/v1/categories", json={"name": "Sport"})
    cat_1_id = cat_1.json()["id"]
    category = await CategoryRepository(session=db_session).get_by_id(cat_1_id)
    assert category is not None

    todo_0 = await TodoRepository(session=db_session).create(
        owner_id=other_user.id, data=TodoCreate(title="Tache other user"), categories=[category]
    )

    todo_1 = await authenticated_admin.post(
        "/api/v1/todos", json={"title": "Tache 1", "category_ids": [cat_1_id]}
    )
    todo_2 = await authenticated_admin.post(
        "/api/v1/todos", json={"title": "Tache 2", "category_ids": [cat_1_id]}
    )

    # 2. Récupération des tâches de la catégorie
    response = await authenticated_admin.get(f"/api/v1/categories/{cat_1_id}/todos")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["items"][0]["id"] == todo_2.json()["id"]
    assert data["items"][1]["id"] == todo_1.json()["id"]
    assert data["items"][2]["id"] == todo_0.id


async def test_get_todos_by_category_empty(authenticated_client: AsyncClient) -> None:
    """An empty list is returned when a category has no todos."""
    cat_1 = await authenticated_client.post("/api/v1/categories", json={"name": "Sport"})
    cat_1_id = cat_1.json()["id"]

    response = await authenticated_client.get(f"/api/v1/categories/{cat_1_id}/todos")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_list_categories_filter_by_name(authenticated_client: AsyncClient) -> None:
    """Checks filtering categories by name."""
    cat_1 = await authenticated_client.post("/api/v1/categories", json={"name": "Sport"})
    cat_2 = await authenticated_client.post("/api/v1/categories", json={"name": "Portable"})
    await authenticated_client.post("/api/v1/categories", json={"name": "House"})

    response = await authenticated_client.get("/api/v1/categories?name=port")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["items"][0] == cat_2.json()
    assert data["items"][1] == cat_1.json()
