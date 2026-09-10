"""
Tests d'intégration des endpoints Todos.
Équivalent conceptuel de tests/Feature/TodoTest.php dans Laravel.
"""

from httpx import AsyncClient


async def test_healthcheck(client: AsyncClient) -> None:
    """Vérifie que l'endpoint /health répond 200 OK."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data


async def test_create_todo_success(client: AsyncClient) -> None:
    """Vérifie la création réussie d'une tâche (POST /api/v1/todos)."""
    payload = {
        "title": "Acheter du café",
        "description": "Café en grains bio",
    }
    response = await client.post("/api/v1/todos", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["is_completed"] is False
    assert "created_at" in data
    assert "updated_at" in data


async def test_create_todo_missing_title_returns_422(client: AsyncClient) -> None:
    """Vérifie que l'omission du titre est rejetée par Pydantic (422 Unprocessable Entity)."""
    response = await client.post("/api/v1/todos", json={"description": "Pas de titre"})
    assert response.status_code == 422


async def test_create_todo_empty_title_returns_422(client: AsyncClient) -> None:
    """Vérifie qu'un titre vide ("") est rejeté grâce à min_length=1."""
    response = await client.post("/api/v1/todos", json={"title": ""})
    assert response.status_code == 422


async def test_create_todo_with_categories(client: AsyncClient) -> None:
    """Vérifie que la création d'une tâche avec des catégories fonctionne"""
    cat_1 = await client.post("/api/v1/categories", json={"name": "Catégorie 1"})
    cat_2 = await client.post("/api/v1/categories", json={"name": "Catégorie 2"})

    payload = {
        "title": "Tâche avec catégories",
        "category_ids": [cat_1.json()["id"], cat_2.json()["id"]],
    }

    response = await client.post("/api/v1/todos", json=payload)
    todo_id = response.json()["id"]
    assert response.json()["title"] == payload["title"]

    detail = await client.get(f"/api/v1/todos/{todo_id}?include=categories")
    assert detail.json()["categories"] == [cat_1.json(), cat_2.json()]


async def test_create_todo_ignore_invalid_category_ids(client: AsyncClient) -> None:
    """Création d'une tâche avec une catégorie inexistante"""
    cat_1 = await client.post("/api/v1/categories", json={"name": "Catégorie 1"})

    payload = {
        "title": "Tâche avec catégorie inexistante",
        "category_ids": [cat_1.json()["id"], 9999],
    }

    response = await client.post("/api/v1/todos", json=payload)
    todo_id = response.json()["id"]
    assert response.json()["title"] == payload["title"]

    detail = await client.get(f"/api/v1/todos/{todo_id}?include=categories")
    assert len(detail.json()["categories"]) == 1
    assert detail.json()["categories"] == [cat_1.json()]


async def test_list_todos(client: AsyncClient) -> None:
    """Vérifie la récupération de la liste des tâches (GET /api/v1/todos)."""
    # 1. Création de deux tâches
    await client.post("/api/v1/todos", json={"title": "Tâche 1"})
    await client.post("/api/v1/todos", json={"title": "Tâche 2"})

    # 2. Récupération de la liste
    response = await client.get("/api/v1/todos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Tâche 2"  # Tri décroissant par ID


async def test_get_todo_by_id_success(client: AsyncClient) -> None:
    """Vérifie la récupération d'une tâche par son ID (GET /api/v1/todos/{id})."""
    create_res = await client.post("/api/v1/todos", json={"title": "Lire Clean Architecture"})
    created_id = create_res.json()["id"]

    response = await client.get(f"/api/v1/todos/{created_id}")
    assert response.status_code == 200
    assert response.json()["id"] == created_id
    assert response.json()["title"] == "Lire Clean Architecture"


async def test_get_todo_without_include_has_no_categories(client: AsyncClient) -> None:
    """Obtenir une tâche sans inclure les catégories"""
    cat_1 = await client.post("/api/v1/categories", json={"name": "Catégorie 1"})
    cat_2 = await client.post("/api/v1/categories", json={"name": "Catégorie 2"})

    payload = {
        "title": "Tâche sans inclure catégories",
        "category_ids": [cat_1.json()["id"], cat_2.json()["id"]],
    }

    todo = await client.post("/api/v1/todos", json=payload)
    todo_id = todo.json()["id"]

    response = await client.get(f"/api/v1/todos/{todo_id}")
    data = response.json()

    assert data["id"] == todo_id
    assert data["title"] == payload["title"]
    assert "categories" not in data


async def test_get_todo_with_include_categories(client: AsyncClient) -> None:
    """Obtenir une tâche en incluant les catégories"""
    cat_1 = await client.post("/api/v1/categories", json={"name": "Catégorie 1"})
    cat_2 = await client.post("/api/v1/categories", json={"name": "Catégorie 2"})

    payload = {
        "title": "Tâche en incluant les catégories",
        "category_ids": [cat_1.json()["id"], cat_2.json()["id"]],
    }

    todo = await client.post("/api/v1/todos", json=payload)
    todo_id = todo.json()["id"]

    response = await client.get(f"/api/v1/todos/{todo_id}?include=categories")
    data = response.json()

    assert data["id"] == todo_id
    assert data["title"] == payload["title"]
    assert "categories" in data
    assert len(data["categories"]) == len(payload["category_ids"])


async def test_get_todo_not_found_returns_404(client: AsyncClient) -> None:
    """Vérifie qu'un ID inexistant renvoie 404 Not Found."""
    response = await client.get("/api/v1/todos/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Tâche avec l'ID 99999 introuvable."


async def test_patch_todo_success(client: AsyncClient) -> None:
    """Vérifie la mise à jour partielle (PATCH /api/v1/todos/{id})."""
    create_res = await client.post(
        "/api/v1/todos", json={"title": "Tâche initiale", "description": "Desc"}
    )
    todo_id = create_res.json()["id"]

    # On ne modifie QUE is_completed
    update_res = await client.patch(f"/api/v1/todos/{todo_id}", json={"is_completed": True})
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["is_completed"] is True
    assert data["title"] == "Tâche initiale"  # Le titre n'a pas été effacé !


async def test_patch_todo_with_null_title_returns_422(client: AsyncClient) -> None:
    """
    Vérifie notre règle 'sometimes|required' :
    Si le client envoie explicitement title=null, Pydantic renvoie une 422.
    """
    create_res = await client.post("/api/v1/todos", json={"title": "Tâche test"})
    todo_id = create_res.json()["id"]

    response = await client.patch(f"/api/v1/todos/{todo_id}", json={"title": None})
    assert response.status_code == 422


async def test_patch_todo_with_null_description_allowed(client: AsyncClient) -> None:
    """Vérifie qu'on peut remettre la description à null (champ nullable)."""
    create_res = await client.post(
        "/api/v1/todos",
        json={"title": "Tâche avec desc", "description": "Description à effacer"},
    )
    todo_id = create_res.json()["id"]

    response = await client.patch(f"/api/v1/todos/{todo_id}", json={"description": None})
    assert response.status_code == 200
    assert response.json()["description"] is None


async def test_update_todo_replaces_categories(client: AsyncClient) -> None:
    """Mettre à jour les catégories d'une tâche"""
    cat_1 = await client.post("/api/v1/categories", json={"name": "Catégorie 1"})
    cat_2 = await client.post("/api/v1/categories", json={"name": "Catégorie 2"})
    cat_3 = await client.post("/api/v1/categories", json={"name": "Catégorie 3"})
    cat_4 = await client.post("/api/v1/categories", json={"name": "Catégorie 4"})

    payload = {
        "title": "Tâche avec catégories à mettre à jour",
        "category_ids": [cat_1.json()["id"], cat_3.json()["id"]],
    }

    todo = await client.post("/api/v1/todos", json=payload)
    todo_id = todo.json()["id"]

    await client.patch(
        f"/api/v1/todos/{todo_id}", json={"category_ids": [cat_2.json()["id"], cat_4.json()["id"]]}
    )

    response = await client.get(f"/api/v1/todos/{todo_id}?include=categories")
    data = response.json()

    assert data["id"] == todo_id
    assert data["title"] == payload["title"]
    assert data["categories"] == [cat_2.json(), cat_4.json()]


async def test_update_todo_clears_categories_with_empty_list(client: AsyncClient) -> None:
    """Vider les catégories d'une tâche avec une liste vide"""
    cat_1 = await client.post("/api/v1/categories", json={"name": "Catégorie 1"})

    payload = {"title": "Tâche avec catégories à vider", "category_ids": [cat_1.json()["id"]]}

    todo = await client.post("/api/v1/todos", json=payload)
    todo_id = todo.json()["id"]

    await client.patch(f"/api/v1/todos/{todo_id}", json={"category_ids": []})

    response = await client.get(f"/api/v1/todos/{todo_id}?include=categories")
    data = response.json()

    assert data["id"] == todo_id
    assert data["title"] == payload["title"]
    assert data["categories"] == []


async def test_update_todo_omits_category_ids_keeps_existing(client: AsyncClient) -> None:
    """Omettre la liste des catégories lors de la mise à jour"""
    cat_1 = await client.post("/api/v1/categories", json={"name": "Catégorie 1"})

    payload = {
        "title": "Tâche avec catégories à mettre à jour",
        "category_ids": [cat_1.json()["id"]],
    }

    todo = await client.post("/api/v1/todos", json=payload)
    todo_id = todo.json()["id"]

    await client.patch(f"/api/v1/todos/{todo_id}", json={"title": "Nouveau titre"})

    response = await client.get(f"/api/v1/todos/{todo_id}?include=categories")
    data = response.json()

    assert data["id"] == todo_id
    assert data["title"] == "Nouveau titre"
    assert data["categories"] == [cat_1.json()]


async def test_delete_todo_success(client: AsyncClient) -> None:
    """Vérifie la suppression d'une tâche (DELETE /api/v1/todos/{id})."""
    create_res = await client.post("/api/v1/todos", json={"title": "Tâche à supprimer"})
    todo_id = create_res.json()["id"]

    # 1. Suppression
    del_res = await client.delete(f"/api/v1/todos/{todo_id}")
    assert del_res.status_code == 204

    # 2. Vérification que la tâche n'existe plus
    get_res = await client.get(f"/api/v1/todos/{todo_id}")
    assert get_res.status_code == 404


async def test_list_filter_by_is_completed(client: AsyncClient) -> None:
    """Vérifie le filtre sur le statut de complétion"""
    todo_1 = await client.post("/api/v1/todos", json={"title": "Tâche 1"})
    await client.post("/api/v1/todos", json={"title": "Tâche 2"})

    # Seule la tâche 1 est marquée comme complétée
    await client.patch(f"/api/v1/todos/{todo_1.json()['id']}", json={"is_completed": True})

    response = await client.get("/api/v1/todos?is_completed=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Tâche 1"

    response = await client.get("/api/v1/todos?is_completed=false")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Tâche 2"


async def test_list_filter_by_category_ids(client: AsyncClient) -> None:
    """Vérifie le filtre par catégories (sémantique union : au moins une des catégories)."""
    cat_a = await client.post("/api/v1/categories", json={"name": "Cat A"})
    cat_b = await client.post("/api/v1/categories", json={"name": "Cat B"})
    cat_c = await client.post("/api/v1/categories", json={"name": "Cat C"})
    cat_a_id = cat_a.json()["id"]
    cat_b_id = cat_b.json()["id"]
    cat_c_id = cat_c.json()["id"]

    await client.post("/api/v1/todos", json={"title": "Tâche A", "category_ids": [cat_a_id]})
    await client.post("/api/v1/todos", json={"title": "Tâche B", "category_ids": [cat_b_id]})
    await client.post("/api/v1/todos", json={"title": "Tâche C", "category_ids": [cat_c_id]})

    response = await client.get(f"/api/v1/todos?category_ids={cat_a_id}&category_ids={cat_b_id}")
    assert response.status_code == 200
    data = response.json()
    titles = {todo["title"] for todo in data}
    assert titles == {"Tâche A", "Tâche B"}
