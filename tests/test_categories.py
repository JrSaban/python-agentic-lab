"""
Tests d'intégration des endpoints Categories.
"""

from httpx import AsyncClient


async def test_create_category_success(client: AsyncClient) -> None:
    """Vérifie la création réussie d'une catégorie (POST /api/v1/categories)."""
    payload = {
        "name": "Sport",
    }
    response = await client.post("/api/v1/categories", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == payload["name"]
    assert data["color"] == "#FAFAFA"
    assert "created_at" in data


async def test_create_category_missing_name_returns_422(client: AsyncClient) -> None:
    """Vérifie que l'omission du nom est rejetée par Pydantic (422 Unprocessable Entity)."""
    response = await client.post("/api/v1/categories", json={"color": "#FF0000"})
    assert response.status_code == 422


async def test_create_category_empty_name_returns_422(client: AsyncClient) -> None:
    """Vérifie qu'un nom vide ("") est rejeté grâce à min_length=1."""
    response = await client.post("/api/v1/categories", json={"name": "", "color": "#FF0000"})
    assert response.status_code == 422


async def test_create_category_empty_color_returns_422(client: AsyncClient) -> None:
    """Vérifie qu'une couleur vide ("") est rejetée grâce au pattern Regex."""
    response = await client.post("/api/v1/categories", json={"name": "Test", "color": ""})
    assert response.status_code == 422


async def test_list_categories(client: AsyncClient) -> None:
    """Vérifie la récupération de la liste des catégories (GET /api/v1/categories)."""
    # 1. Création de deux catégories
    await client.post("/api/v1/categories", json={"name": "Sport"})
    await client.post("/api/v1/categories", json={"name": "House", "color": "#00FF00"})

    # 2. Récupération de la liste
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["items"][0]["name"] == "House"  # Tri croissant par nom


async def test_get_category_by_id_success(client: AsyncClient) -> None:
    """Vérifie la récupération d'une catégorie par son ID (GET /api/v1/categories/{id})."""
    create_res = await client.post("/api/v1/categories", json={"name": "Sport", "color": "#FF0000"})
    created_id = create_res.json()["id"]

    response = await client.get(f"/api/v1/categories/{created_id}")
    assert response.status_code == 200
    assert response.json()["id"] == created_id
    assert response.json()["name"] == "Sport"
    assert response.json()["color"] == "#FF0000"


async def test_get_category_not_found_returns_404(client: AsyncClient) -> None:
    """Vérifie qu'un ID inexistant renvoie 404 Not Found."""
    response = await client.get("/api/v1/categories/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Catégorie avec l'ID 99999 introuvable."


async def test_patch_category_success(client: AsyncClient) -> None:
    """Vérifie la mise à jour partielle (PATCH /api/v1/categories/{id})."""
    create_res = await client.post("/api/v1/categories", json={"name": "Sport", "color": "#FF0000"})
    category_id = create_res.json()["id"]

    # On ne modifie QUE name
    update_res = await client.patch(f"/api/v1/categories/{category_id}", json={"name": "House"})
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["name"] == "House"
    assert data["color"] == "#FF0000"  # La couleur n'a pas été effacée !


async def test_patch_category_with_null_name_returns_422(client: AsyncClient) -> None:
    """
    Si le client envoie explicitement name=null, Pydantic renvoie une 422.
    """
    create_res = await client.post("/api/v1/categories", json={"name": "Sport"})
    category_id = create_res.json()["id"]

    response = await client.patch(f"/api/v1/categories/{category_id}", json={"name": None})
    assert response.status_code == 422


async def test_delete_category_success(client: AsyncClient) -> None:
    """Vérifie la suppression d'une catégorie (DELETE /api/v1/categories/{id})."""
    create_res = await client.post("/api/v1/categories", json={"name": "Sport"})
    category_id = create_res.json()["id"]

    # 1. Suppression
    del_res = await client.delete(f"/api/v1/categories/{category_id}")
    assert del_res.status_code == 204

    # 2. Vérification que la catégorie n'existe plus
    get_res = await client.get(f"/api/v1/categories/{category_id}")
    assert get_res.status_code == 404


async def test_create_category_duplicate_name_returns_409(client: AsyncClient) -> None:
    """Vérifie qu'une catégorie avec le même nom n'est pas acceptée (409 Conflict)."""
    # 1. Création de la catégorie
    await client.post("/api/v1/categories", json={"name": "Sport"})

    # 2. Tentative de création de la même catégorie
    response = await client.post("/api/v1/categories", json={"name": "Sport"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Une catégorie avec le nom Sport existe déjà."


async def test_create_category_case_insensitive_duplicate_returns_409(client: AsyncClient) -> None:
    """Vérifie qu'un nom en doublon, en majuscules, n'est pas accepté (409 Conflict)."""
    # 1. Création de la catégorie en minuscules
    await client.post("/api/v1/categories", json={"name": "Sport"})

    # 2. Tentative de création de la même catégorie en majuscules
    response = await client.post("/api/v1/categories", json={"name": "SPORT"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Une catégorie avec le nom SPORT existe déjà."


async def test_create_category_uppercases_color(client: AsyncClient) -> None:
    """Vérifie que le champ color soit transformé en majuscules."""
    create_res = await client.post("/api/v1/categories", json={"name": "Sport", "color": "#fbfbfb"})
    category_id = create_res.json()["id"]

    category = await client.get(f"/api/v1/categories/{category_id}")
    assert category.status_code == 200
    assert category.json()["id"] == category_id
    assert category.json()["name"] == "Sport"
    assert category.json()["color"] == "#FBFBFB"


async def test_update_category_name_conflict_returns_409(client: AsyncClient) -> None:
    """Vérifie que renommer une catégorie avec le nom d'une autre existante renvoie 409."""
    # 1. Création de deux catégories
    await client.post("/api/v1/categories", json={"name": "House"})
    create_res = await client.post("/api/v1/categories", json={"name": "Sport"})
    category_id = create_res.json()["id"]

    # 2. Tentative de renommer la catégorie "Sport" en "house"
    response = await client.patch(f"/api/v1/categories/{category_id}", json={"name": "house"})
    assert response.status_code == 409
    assert response.json()["detail"] == "Une catégorie avec le nom house existe déjà."


async def test_update_category_keep_same_name_succeeds(client: AsyncClient) -> None:
    """Vérifie que renommer une catégorie avec le même nom ne provoque pas d'erreur 409 Conflict."""
    # 1. Création de la catégorie
    create_res = await client.post("/api/v1/categories", json={"name": "sport"})
    category_id = create_res.json()["id"]

    # 2. Tentative de renommer la catégorie "sport" en "Sport"
    response = await client.patch(f"/api/v1/categories/{category_id}", json={"name": "Sport"})
    assert response.status_code == 200
    assert response.json()["id"] == category_id
    assert response.json()["name"] == "Sport"


async def test_get_todos_by_category(client: AsyncClient) -> None:
    """Vérifie qu'on peut récupérer les tâches associées à une catégorie."""
    cat_1 = await client.post("/api/v1/categories", json={"name": "Sport"})
    cat_1_id = cat_1.json()["id"]

    todo_1 = await client.post(
        "/api/v1/todos", json={"title": "Tache 1", "category_ids": [cat_1_id]}
    )
    todo_2 = await client.post(
        "/api/v1/todos", json={"title": "Tache 2", "category_ids": [cat_1_id]}
    )

    # 2. Récupération des tâches de la catégorie
    response = await client.get(f"/api/v1/categories/{cat_1_id}/todos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == todo_1.json()["id"]
    assert data[1]["id"] == todo_2.json()["id"]


async def test_get_todos_by_category_empty(client: AsyncClient) -> None:
    """Vérifie qu'on récupère une liste vide quand une catégorie n'a pas de tâches."""
    cat_1 = await client.post("/api/v1/categories", json={"name": "Sport"})
    cat_1_id = cat_1.json()["id"]

    response = await client.get(f"/api/v1/categories/{cat_1_id}/todos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0
    assert data == []


async def test_list_categories_filter_by_name(client: AsyncClient) -> None:
    """Vérifie qu'on peut filtrer les catégories par nom."""
    cat_1 = await client.post("/api/v1/categories", json={"name": "Sport"})
    cat_2 = await client.post("/api/v1/categories", json={"name": "Portable"})
    await client.post("/api/v1/categories", json={"name": "House"})

    response = await client.get("/api/v1/categories?name=port")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["items"][0] == cat_2.json()
    assert data["items"][1] == cat_1.json()
