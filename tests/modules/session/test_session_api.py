from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from apps.config import app_settings
from apps.modules.user import User
from apps.shared import apps_types
from tests.modules.session.fakes import RefreshTokensStorage

NAME = "Артём"
EMAIL = "name@example.com"
PASSWORD = "s3cret-Passw0rd"


def _register(client: TestClient, email: str = EMAIL) -> None:
    response = client.post(
        "/auth/registration",
        json={"name": NAME, "email": email, "password": PASSWORD, "password_confirmation": PASSWORD},
    )
    assert response.status_code == 201


def _login(client: TestClient, email: str = EMAIL) -> dict[str, Any]:
    response = client.post("/auth/token", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def _refresh(client: TestClient, refresh_token: str) -> Response:
    return client.post("/auth/token/refresh", json={"refresh_token": refresh_token})


def _logout(client: TestClient, access_token: str, refresh_token: str) -> Response:
    return client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )


def _assert_invalid_refresh(response: Response) -> None:
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "FM-401002"
    assert body["instance"] == "/auth/token/refresh"
    assert response.headers["content-type"] == "application/problem+json"


def _assert_token_pair(body: dict[str, Any]) -> None:
    assert set(body) == {"access_token", "refresh_token", "token_type", "expires_in"}
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == app_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert body["access_token"]
    assert body["refresh_token"]


@pytest.fixture
def session(client: TestClient) -> dict[str, Any]:
    """Пара токенов зарегистрированного и вошедшего пользователя."""
    _register(client)
    return _login(client)


# --- Вход ---


def test_login_returns_token_pair(session: dict[str, Any]) -> None:
    _assert_token_pair(session)


def test_login_expires_in_follows_access_token_lifetime(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15)
    _register(client)

    assert _login(client)["expires_in"] == 900


def test_refresh_token_is_opaque_not_jwt(session: dict[str, Any]) -> None:
    assert session["refresh_token"].count(".") != 2
    assert session["refresh_token"] != session["access_token"]


def test_each_login_issues_new_refresh_token(client: TestClient) -> None:
    _register(client)

    assert _login(client)["refresh_token"] != _login(client)["refresh_token"]


def test_refresh_token_is_stored_only_as_hash(
    session: dict[str, Any],
    users_storage: dict[apps_types.UserUID, User],
    refresh_tokens_storage: RefreshTokensStorage,
) -> None:
    [stored] = refresh_tokens_storage.values()
    [user] = users_storage.values()
    assert stored.user_uid == user.uid
    assert stored.revoked is False
    assert stored.token_hash != session["refresh_token"]
    assert session["refresh_token"] not in repr(stored.model_dump())


def test_refresh_token_lifetime_comes_from_settings(
    client: TestClient,
    refresh_tokens_storage: RefreshTokensStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_settings, "REFRESH_TOKEN_EXPIRE_DAYS", 3)
    _register(client)
    before = datetime.now(tz=UTC)

    _login(client)

    [stored] = refresh_tokens_storage.values()
    assert abs((stored.expires_at - (before + timedelta(days=3))).total_seconds()) < 5


# --- Обновление ---


def test_refresh_returns_new_working_pair(client: TestClient, session: dict[str, Any]) -> None:
    response = _refresh(client, session["refresh_token"])

    assert response.status_code == 200
    body = response.json()
    _assert_token_pair(body)
    assert body["refresh_token"] != session["refresh_token"]
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}).status_code == 200
    assert _refresh(client, body["refresh_token"]).status_code == 200


def test_refresh_token_is_rotated(client: TestClient, session: dict[str, Any]) -> None:
    assert _refresh(client, session["refresh_token"]).status_code == 200

    _assert_invalid_refresh(_refresh(client, session["refresh_token"]))


def test_unknown_refresh_token_is_rejected(client: TestClient, session: dict[str, Any]) -> None:
    _assert_invalid_refresh(_refresh(client, "unknown-token"))


def test_access_token_is_not_accepted_as_refresh_token(client: TestClient, session: dict[str, Any]) -> None:
    _assert_invalid_refresh(_refresh(client, session["access_token"]))


def test_expired_refresh_token_is_rejected(
    client: TestClient,
    session: dict[str, Any],
    refresh_tokens_storage: RefreshTokensStorage,
) -> None:
    for uid, token in refresh_tokens_storage.items():
        refresh_tokens_storage[uid] = token.model_copy(
            update={"expires_at": datetime.now(tz=UTC) - timedelta(seconds=1)},
        )

    _assert_invalid_refresh(_refresh(client, session["refresh_token"]))


def test_refresh_of_deleted_user_is_rejected(
    client: TestClient,
    session: dict[str, Any],
    users_storage: dict[apps_types.UserUID, User],
) -> None:
    users_storage.clear()

    _assert_invalid_refresh(_refresh(client, session["refresh_token"]))


@pytest.mark.parametrize("body", [{}, {"refresh_token": ""}, {"refresh_token": "x" * 513}])
def test_refresh_validates_body(client: TestClient, body: dict[str, Any]) -> None:
    response = client.post("/auth/token/refresh", json=body)

    assert response.status_code == 422
    assert response.json()["code"] == "FM-422000"


def test_refresh_rejects_unknown_fields(client: TestClient, session: dict[str, Any]) -> None:
    response = client.post("/auth/token/refresh", json={"refresh_token": session["refresh_token"], "extra": 1})

    assert response.status_code == 422


def test_refresh_token_is_not_echoed_in_validation_error(client: TestClient) -> None:
    secret = "s3cret-refresh-" + "x" * 500

    response = client.post("/auth/token/refresh", json={"refresh_token": secret})

    assert response.status_code == 422
    [item] = response.json()["validation"]
    assert item["field"] == "refresh_token"
    assert item["rejectedValue"] is None
    assert secret not in response.text


# --- Выход ---


def test_logout_revokes_refresh_token(client: TestClient, session: dict[str, Any]) -> None:
    response = _logout(client, session["access_token"], session["refresh_token"])

    assert response.status_code == 204
    assert response.content == b""
    _assert_invalid_refresh(_refresh(client, session["refresh_token"]))


def test_access_token_keeps_working_after_logout(client: TestClient, session: dict[str, Any]) -> None:
    assert _logout(client, session["access_token"], session["refresh_token"]).status_code == 204

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {session['access_token']}"})

    assert response.status_code == 200


def test_repeated_logout_returns_no_content(client: TestClient, session: dict[str, Any]) -> None:
    assert _logout(client, session["access_token"], session["refresh_token"]).status_code == 204

    assert _logout(client, session["access_token"], session["refresh_token"]).status_code == 204


def test_logout_with_unknown_refresh_token_returns_no_content(client: TestClient, session: dict[str, Any]) -> None:
    assert _logout(client, session["access_token"], "unknown-token").status_code == 204


def test_logout_does_not_revoke_refresh_token_of_another_user(client: TestClient, session: dict[str, Any]) -> None:
    _register(client, email="other@example.com")
    other = _login(client, email="other@example.com")

    assert _logout(client, session["access_token"], other["refresh_token"]).status_code == 204

    assert _refresh(client, other["refresh_token"]).status_code == 200


def test_logout_requires_access_token(client: TestClient, session: dict[str, Any]) -> None:
    response = client.post("/auth/logout", json={"refresh_token": session["refresh_token"]})

    assert response.status_code == 401
    assert response.json()["code"] == "FM-401000"
    assert _refresh(client, session["refresh_token"]).status_code == 200


@pytest.mark.parametrize("body", [{}, {"refresh_token": ""}, {"refresh_token": "x" * 513}, {"token": "x"}])
def test_logout_validates_body(client: TestClient, session: dict[str, Any], body: dict[str, Any]) -> None:
    response = client.post("/auth/logout", json=body, headers={"Authorization": f"Bearer {session['access_token']}"})

    assert response.status_code == 422
