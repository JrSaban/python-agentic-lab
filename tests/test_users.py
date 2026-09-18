"""Tests d'intégration des endpoints Users."""

from httpx import AsyncClient

from src.modules.users.models import User


async def test_create_user_success(client: AsyncClient) -> None:
    """Successful registration (POST /api/v1/users) → 201, no password in the response."""
    payload = {
        "email": "test@gmail.com",
        "first_name": "John",
        "last_name": "Doe",
        "pseudo": "JohnDoe",
        "password": "password",
        "confirm_password": "password",
    }

    response = await client.post("/api/v1/users", json=payload)
    assert response.status_code == 201
    assert response.json()["email"] == "test@gmail.com"
    assert "password" not in response.json()


async def test_create_user_duplicate_email_returns_409(client: AsyncClient) -> None:
    """Two registrations with the same email → the second one returns 409."""
    first_user = {
        "email": "test@gmail.com",
        "first_name": "John",
        "last_name": "Doe",
        "pseudo": "JohnDoe",
        "password": "password",
        "confirm_password": "password",
    }
    second_user = {
        "email": "test@gmail.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "pseudo": "JaneDoe",
        "password": "password",
        "confirm_password": "password",
    }

    response = await client.post("/api/v1/users", json=first_user)
    assert response.status_code == 201

    response = await client.post("/api/v1/users", json=second_user)
    assert response.status_code == 409


async def test_create_user_missing_fields_returns_422(client: AsyncClient) -> None:
    """Registration with missing required fields → 422."""
    first_payload = {
        "first_name": "John",
        "last_name": "Doe",
        "pseudo": "JohnDoe",
        "password": "password",
        "confirm_password": "password",
    }
    second_payload = {
        "email": "test@gmail.com",
        "first_name": "John",
        "last_name": "Doe",
        "password": "password",
    }
    third_payload = {
        "email": "test@gmail.com",
        "last_name": "Doe",
        "password": "password",
        "confirm_password": "password",
    }

    response = await client.post("/api/v1/users", json=first_payload)
    assert response.status_code == 422
    response = await client.post("/api/v1/users", json=second_payload)
    assert response.status_code == 422
    response = await client.post("/api/v1/users", json=third_payload)
    assert response.status_code == 422


async def test_list_users_as_admin_success(authenticated_admin: AsyncClient) -> None:
    """An admin can list users (GET /api/v1/users) → 200, paginated response."""
    response = await authenticated_admin.get("/api/v1/users")
    assert response.status_code == 200


async def test_list_users_as_regular_user_returns_403(authenticated_client: AsyncClient) -> None:
    """A regular user cannot list users → 403."""
    response = await authenticated_client.get("/api/v1/users")
    assert response.status_code == 403


async def test_get_me_with_real_token(client: AsyncClient) -> None:
    """
    Real registration + real login (not the shortcut fixtures), then GET /users/me
    with the real token obtained → 200. Verifies the real authentication mechanism
    (not just the permission logic) works end to end.
    """
    response = await client.post(
        "/api/v1/users",
        json={
            "email": "test@gmail.com",
            "first_name": "John",
            "last_name": "Doe",
            "pseudo": "JohnDoe",
            "password": "password",
            "confirm_password": "password",
        },
    )
    assert response.status_code == 201
    response = await client.post(
        "/api/v1/login", json={"email": "test@gmail.com", "password": "password"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

    access_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "test@gmail.com"


async def test_get_me_without_token_returns_401(client: AsyncClient) -> None:
    """GET /users/me with no Authorization header at all → 401."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_get_user_self_success(authenticated_client: AsyncClient, current_user: User) -> None:
    """A user can view their own profile (GET /api/v1/users/{id}) → 200."""
    response = await authenticated_client.get(f"/api/v1/users/{current_user.id}")
    assert response.status_code == 200
    assert response.json()["id"] == current_user.id


async def test_get_user_as_admin_success(
    authenticated_admin: AsyncClient, current_admin_user: User, current_user: User
) -> None:
    """An admin can view any user's profile → 200."""
    response = await authenticated_admin.get(f"/api/v1/users/{current_user.id}")
    assert response.status_code == 200
    assert response.json()["id"] == current_user.id
    assert current_admin_user.id != current_user.id
    assert current_admin_user.is_admin is True


async def test_get_user_as_regular_user_on_other_returns_403(
    authenticated_client: AsyncClient, current_admin_user: User
) -> None:
    """A regular user cannot view another user's profile → 403."""
    response = await authenticated_client.get(f"/api/v1/users/{current_admin_user.id}")
    assert response.status_code == 403


async def test_get_user_not_found_as_admin_returns_404(authenticated_admin: AsyncClient) -> None:
    """An admin looking up a non-existent ID → 404."""
    response = await authenticated_admin.get("/api/v1/users/999")
    assert response.status_code == 404


async def test_update_user_self_success(
    authenticated_client: AsyncClient, current_user: User
) -> None:
    """A user can update their own profile (PATCH /api/v1/users/{id}) → 200."""
    assert current_user.email == "user@test.com"
    response = await authenticated_client.patch(
        f"/api/v1/users/{current_user.id}", json={"email": "test@gmail.com"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == current_user.id
    assert response.json()["email"] == "test@gmail.com"


async def test_update_user_other_as_regular_user_returns_403(
    authenticated_client: AsyncClient, current_admin_user: User
) -> None:
    """A regular user cannot update another user's profile → 403."""
    response = await authenticated_client.patch(
        f"/api/v1/users/{current_admin_user.id}", json={"email": "test@gmail.com"}
    )
    assert response.status_code == 403


async def test_update_password_success(
    client: AsyncClient, authenticated_client: AsyncClient, current_user: User
) -> None:
    """
    Successful password change (PATCH /api/v1/users/me/password) → 200,
    then verify you can log back in (POST /api/v1/login) with the NEW password.
    """
    response = await authenticated_client.patch(
        "/api/v1/users/me/password",
        json={
            "new_password": "new_password",
            "old_password": "secret123",
            "confirm_new_password": "new_password",
        },
    )
    assert response.status_code == 200
    assert response.json()["id"] == current_user.id

    response = await client.post(
        "/api/v1/login", json={"email": current_user.email, "password": "new_password"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_update_password_wrong_old_password_returns_403(
    authenticated_client: AsyncClient,
) -> None:
    """Password change with an incorrect old password → 403."""
    response = await authenticated_client.patch(
        "/api/v1/users/me/password",
        json={
            "new_password": "new_password",
            "old_password": "wrong_password",
            "confirm_new_password": "new_password",
        },
    )
    assert response.status_code == 403


async def test_set_user_active_as_admin_success(
    authenticated_admin: AsyncClient, current_user: User
) -> None:
    """An admin can activate/deactivate another user (PATCH .../active) → 200."""
    assert current_user.is_active is True
    response = await authenticated_admin.patch(
        f"/api/v1/users/{current_user.id}/active", json={"is_active": False}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_set_user_active_as_regular_user_returns_403(
    authenticated_client: AsyncClient, current_admin_user: User
) -> None:
    """A regular user cannot activate/deactivate an account → 403."""
    response = await authenticated_client.patch(
        f"/api/v1/users/{current_admin_user.id}/active", json={"is_active": False}
    )
    assert response.status_code == 403


async def test_set_user_active_last_admin_returns_403(
    authenticated_admin: AsyncClient, current_admin_user: User
) -> None:
    """Deactivating the last admin (themselves, if they're the only one) → 403."""
    response = await authenticated_admin.patch(
        f"/api/v1/users/{current_admin_user.id}/active", json={"is_active": False}
    )
    assert response.status_code == 403


async def test_set_user_admin_as_admin_success(
    authenticated_admin: AsyncClient, current_user: User
) -> None:
    """An admin can change another user's admin status (PATCH .../admin) → 200."""
    assert current_user.is_admin is False
    response = await authenticated_admin.patch(
        f"/api/v1/users/{current_user.id}/admin", json={"is_admin": True}
    )
    assert response.status_code == 200
    assert response.json()["is_admin"] is True


async def test_set_user_admin_as_regular_user_returns_403(
    authenticated_client: AsyncClient, current_admin_user: User
) -> None:
    """A regular user cannot change someone's admin status → 403."""
    response = await authenticated_client.patch(
        f"/api/v1/users/{current_admin_user.id}/admin", json={"is_admin": False}
    )
    assert response.status_code == 403
