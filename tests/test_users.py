"""Tests d'intégration des endpoints Users."""

from httpx import AsyncClient

from src.core.config import settings
from src.modules.users.models import User

# --- create_user ---


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


async def test_create_user_duplicate_pseudo_returns_409(client: AsyncClient) -> None:
    """Two registrations with the same pseudo → the second one returns 409."""
    first_user = {
        "email": "test@gmail.com",
        "first_name": "John",
        "last_name": "Doe",
        "pseudo": "JohnDoe",
        "password": "password",
        "confirm_password": "password",
    }
    second_user = {
        "email": "jane@gmail.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "pseudo": "JohnDoe",
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


# --- list_users ---


async def test_list_users_as_admin_success(authenticated_admin: AsyncClient) -> None:
    """An admin can list users (GET /api/v1/users) → 200, paginated response."""
    response = await authenticated_admin.get("/api/v1/users")
    assert response.status_code == 200


async def test_list_users_filter_by_name_escapes_wildcards(
    authenticated_admin: AsyncClient,
) -> None:
    """The first_name/last_name search is built by hand (not through
    BaseRepository._apply_filter_params), but still escapes % and _ literally."""
    target = await authenticated_admin.post(
        "/api/v1/users",
        json={
            "email": "a@test.com",
            "first_name": "50%",
            "last_name": "Doe",
            "pseudo": "Target",
            "password": "password",
            "confirm_password": "password",
        },
    )
    await authenticated_admin.post(
        "/api/v1/users",
        json={
            "email": "b@test.com",
            "first_name": "50X",
            "last_name": "Doe",
            "pseudo": "Other",
            "password": "password",
            "confirm_password": "password",
        },
    )

    response = await authenticated_admin.get("/api/v1/users", params={"name": "50%"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == target.json()["id"]


async def test_list_users_as_regular_user_returns_403(authenticated_client: AsyncClient) -> None:
    """A regular user cannot list users → 403."""
    response = await authenticated_client.get("/api/v1/users")
    assert response.status_code == 403


# --- get_user_or_404 (get_me / get_user) ---


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


# --- update_user ---


async def test_update_user_self_success(
    authenticated_client: AsyncClient, current_user: User
) -> None:
    """A user can update their own profile (PATCH /api/v1/users/{id}) → 200. Email
    isn't part of this payload anymore (see the update_email section below)."""
    response = await authenticated_client.patch(
        f"/api/v1/users/{current_user.id}", json={"first_name": "Jeanne"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == current_user.id
    assert response.json()["first_name"] == "Jeanne"


async def test_update_user_other_as_regular_user_returns_403(
    authenticated_client: AsyncClient, current_admin_user: User
) -> None:
    """A regular user cannot update another user's profile → 403."""
    response = await authenticated_client.patch(
        f"/api/v1/users/{current_admin_user.id}", json={"first_name": "Jeanne"}
    )
    assert response.status_code == 403


async def test_update_user_ignores_email(
    authenticated_client: AsyncClient, current_user: User
) -> None:
    """An `email` sent to the general PATCH /api/v1/users/{id} is silently dropped:
    the request succeeds, the other fields are applied, and the email is unchanged.
    Changing it has to go through the password-gated /users/me/email."""
    original_email = current_user.email

    response = await authenticated_client.patch(
        f"/api/v1/users/{current_user.id}",
        json={"first_name": "Jeanne", "email": "hacker@test.com"},
    )
    assert response.status_code == 200
    assert response.json()["first_name"] == "Jeanne"
    assert response.json()["email"] == original_email


# --- update_email ---


async def test_update_email_success(authenticated_client: AsyncClient, current_user: User) -> None:
    """Successful self-service email change (PATCH /api/v1/users/me/email) → 200."""
    response = await authenticated_client.patch(
        "/api/v1/users/me/email",
        json={"new_email": "new@test.com", "current_password": "secret123"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == current_user.id
    assert response.json()["email"] == "new@test.com"


async def test_update_email_wrong_password_returns_403(
    authenticated_client: AsyncClient,
) -> None:
    """Email change with an incorrect current password → 403."""
    response = await authenticated_client.patch(
        "/api/v1/users/me/email",
        json={"new_email": "new@test.com", "current_password": "wrong_password"},
    )
    assert response.status_code == 403


async def test_update_email_duplicate_returns_409(
    authenticated_client: AsyncClient, other_user: User
) -> None:
    """Changing your email to one already taken by another user → 409."""
    response = await authenticated_client.patch(
        "/api/v1/users/me/email",
        json={"new_email": other_user.email, "current_password": "secret123"},
    )
    assert response.status_code == 409


async def test_update_email_revokes_refresh_token(
    authenticated_client: AsyncClient, current_user: User
) -> None:
    """Changing your email revokes your current refresh token, same mechanism as
    a password change or logout."""
    login_response = await authenticated_client.post(
        "/api/v1/login", json={"email": current_user.email, "password": "secret123"}
    )
    refresh_token = login_response.json()["refresh_token"]

    response = await authenticated_client.patch(
        "/api/v1/users/me/email",
        json={"new_email": "new@test.com", "current_password": "secret123"},
    )
    assert response.status_code == 200

    refresh_response = await authenticated_client.post(
        "/api/v1/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 401


async def test_update_email_failure_does_not_revoke_refresh_token(
    authenticated_client: AsyncClient, current_user: User
) -> None:
    """An unsuccessful email change (wrong current password) never reaches the
    revocation step — the existing refresh token keeps working."""
    login_response = await authenticated_client.post(
        "/api/v1/login", json={"email": current_user.email, "password": "secret123"}
    )
    refresh_token = login_response.json()["refresh_token"]

    response = await authenticated_client.patch(
        "/api/v1/users/me/email",
        json={"new_email": "new@test.com", "current_password": "wrong_password"},
    )
    assert response.status_code == 403

    refresh_response = await authenticated_client.post(
        "/api/v1/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200


# --- update_password ---


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


async def test_update_password_revokes_refresh_token(
    authenticated_client: AsyncClient, current_user: User
) -> None:
    """Changing your password revokes your current refresh token, forcing a new
    login — same mechanism (AuthService.revoke_session) as logout."""
    login_response = await authenticated_client.post(
        "/api/v1/login", json={"email": current_user.email, "password": "secret123"}
    )
    refresh_token = login_response.json()["refresh_token"]

    response = await authenticated_client.patch(
        "/api/v1/users/me/password",
        json={
            "new_password": "new_password",
            "old_password": "secret123",
            "confirm_new_password": "new_password",
        },
    )
    assert response.status_code == 200

    refresh_response = await authenticated_client.post(
        "/api/v1/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 401


async def test_update_password_failure_does_not_revoke_refresh_token(
    authenticated_client: AsyncClient, current_user: User
) -> None:
    """An unsuccessful password change (wrong old password) never reaches the
    revocation step — the existing refresh token keeps working."""
    login_response = await authenticated_client.post(
        "/api/v1/login", json={"email": current_user.email, "password": "secret123"}
    )
    refresh_token = login_response.json()["refresh_token"]

    response = await authenticated_client.patch(
        "/api/v1/users/me/password",
        json={
            "new_password": "new_password",
            "old_password": "wrong_password",
            "confirm_new_password": "new_password",
        },
    )
    assert response.status_code == 403

    refresh_response = await authenticated_client.post(
        "/api/v1/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200


# --- sensitive action rate limit (update_email / update_password) ---


async def test_sensitive_action_rate_limit_blocks_after_max_attempts(
    authenticated_client: AsyncClient,
) -> None:
    """Wrong old_password repeated up to SENSITIVE_RATE_LIMIT_MAX_ATTEMPTS times on
    /me/password still returns 403; the next attempt is blocked with 429."""
    for _ in range(settings.SENSITIVE_RATE_LIMIT_MAX_ATTEMPTS):
        response = await authenticated_client.patch(
            "/api/v1/users/me/password",
            json={
                "new_password": "new_password",
                "old_password": "wrong_password",
                "confirm_new_password": "new_password",
            },
        )
        assert response.status_code == 403

    response = await authenticated_client.patch(
        "/api/v1/users/me/password",
        json={
            "new_password": "new_password",
            "old_password": "wrong_password",
            "confirm_new_password": "new_password",
        },
    )
    assert response.status_code == 429


async def test_sensitive_action_rate_limit_shared_between_email_and_password(
    authenticated_client: AsyncClient,
) -> None:
    """Failures on /me/email and /me/password share the same counter: exhausting it
    on one endpoint blocks the other, even with an otherwise-correct password."""
    for _ in range(settings.SENSITIVE_RATE_LIMIT_MAX_ATTEMPTS):
        response = await authenticated_client.patch(
            "/api/v1/users/me/email",
            json={"new_email": "new@test.com", "current_password": "wrong_password"},
        )
        assert response.status_code == 403

    response = await authenticated_client.patch(
        "/api/v1/users/me/password",
        json={
            "new_password": "new_password",
            "old_password": "secret123",
            "confirm_new_password": "new_password",
        },
    )
    assert response.status_code == 429


async def test_sensitive_action_rate_limit_not_triggered_by_repeated_success(
    authenticated_client: AsyncClient,
) -> None:
    """Successful email changes never increment the counter, no matter how many
    in a row."""
    for i in range(settings.SENSITIVE_RATE_LIMIT_MAX_ATTEMPTS + 2):
        response = await authenticated_client.patch(
            "/api/v1/users/me/email",
            json={"new_email": f"new{i}@test.com", "current_password": "secret123"},
        )
        assert response.status_code == 200


# --- set_user_email ---


async def test_set_user_email_by_admin_success(
    authenticated_admin: AsyncClient, other_user: User
) -> None:
    """An admin can change another user's email (PATCH /users/{id}/email) → 200."""
    response = await authenticated_admin.patch(
        f"/api/v1/users/{other_user.id}/email", json={"new_email": "new@test.com"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == other_user.id
    assert response.json()["email"] == "new@test.com"


async def test_set_user_email_by_non_admin_returns_403(
    authenticated_client: AsyncClient, other_user: User
) -> None:
    """A non-admin can't change another user's email → 403."""
    response = await authenticated_client.patch(
        f"/api/v1/users/{other_user.id}/email", json={"new_email": "new@test.com"}
    )
    assert response.status_code == 403


async def test_set_user_email_on_own_id_returns_403(
    authenticated_admin: AsyncClient, current_admin_user: User
) -> None:
    """An admin can't use this admin-only route on their own id — they must go
    through /me/email with their password instead."""
    response = await authenticated_admin.patch(
        f"/api/v1/users/{current_admin_user.id}/email", json={"new_email": "new@test.com"}
    )
    assert response.status_code == 403


async def test_set_user_email_revokes_target_refresh_token(
    authenticated_admin: AsyncClient, other_user: User
) -> None:
    """An admin changing someone else's email revokes THAT user's session, not
    the admin's own."""
    login_response = await authenticated_admin.post(
        "/api/v1/login", json={"email": other_user.email, "password": "secret123"}
    )
    other_user_refresh_token = login_response.json()["refresh_token"]

    response = await authenticated_admin.patch(
        f"/api/v1/users/{other_user.id}/email", json={"new_email": "new@test.com"}
    )
    assert response.status_code == 200

    refresh_response = await authenticated_admin.post(
        "/api/v1/refresh", json={"refresh_token": other_user_refresh_token}
    )
    assert refresh_response.status_code == 401


# --- set_user_active ---


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


# --- set_user_admin ---


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
