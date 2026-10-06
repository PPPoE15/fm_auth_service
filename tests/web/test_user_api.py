from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from apps import apps_types
from apps.config import app_settings
from apps.web.app.aggregators.models import User
from apps.web.app.handlers.api.user import deps
from apps.web.main import build_app
from apps.web.security import UserInfo, get_user_info
from tests.conftest import InMemoryUserUnitOfWork, generate_rsa_pem_pair

LOGIN = "artem"
PASSWORD = "s3cret-Passw0rd"


@pytest.fixture
def app(users_storage: dict[apps_types.UserUID, User], monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Приложение сервиса с хранилищем пользователей в памяти и тестовым защищённым эндпоинтом."""
    monkeypatch.setattr(deps, "UserUnitOfWork", lambda **_: InMemoryUserUnitOfWork(users_storage))
    fastapi_app = build_app()

    @fastapi_app.get("/test/me")
    async def me(user_info: UserInfo = Depends(get_user_info)) -> dict[str, Any]:
        return {"uid": str(user_info.uid), "login": user_info.login}

    return fastapi_app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _register(client: TestClient, login: str = LOGIN, password: str = PASSWORD) -> Response:
    return client.post(
        "/auth/registration",
        json={"login": login, "password": password, "password_confirmation": password, "email": None},
    )


def _login(client: TestClient, login: str = LOGIN, password: str = PASSWORD) -> Response:
    return client.post("/auth/token", json={"login": login, "password": password})


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "sub": "6f9619ff-8b86-4011-b42d-00c04fc964ff",
        "login": LOGIN,
        "exp": datetime.now(tz=UTC) + timedelta(minutes=5),
    }
    payload.update(overrides)
    return {key: value for key, value in payload.items() if value is not None}


def _get_me(client: TestClient, token: str) -> Response:
    return client.get("/test/me", headers={"Authorization": f"Bearer {token}"})


# --- Регистрация ---


def test_registration_returns_user_uid(client: TestClient, users_storage: dict[apps_types.UserUID, User]) -> None:
    response = _register(client)

    assert response.status_code == 200
    [user] = users_storage.values()
    assert response.json() == str(user.uid)
    assert user.login == LOGIN
    assert user.password_hash != PASSWORD


def test_registration_of_existing_login_returns_conflict(client: TestClient) -> None:
    assert _register(client).status_code == 200

    response = _register(client)

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "FM-409001"
    assert body["status"] == 409
    assert LOGIN in body["detail"]
    assert "уже существует" in body["detail"]
    assert body["instance"] == "/auth/registration"


def test_registration_with_mismatched_passwords_returns_bad_request(client: TestClient) -> None:
    response = client.post(
        "/auth/registration",
        json={"login": LOGIN, "password": PASSWORD, "password_confirmation": "other", "email": None},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Пароли не совпадают"


# --- Вход ---


def test_login_returns_token_signed_with_configured_key(
    client: TestClient,
    users_storage: dict[apps_types.UserUID, User],
    signing_keys: tuple[bytes, bytes],
) -> None:
    _register(client)
    before = datetime.now(tz=UTC)

    response = _login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert jwt.get_unverified_header(body["access_token"])["alg"] == "RS256"
    public_pem = signing_keys[1]
    payload = jwt.decode(body["access_token"], key=public_pem, algorithms=["RS256"])
    [user] = users_storage.values()
    assert payload["sub"] == str(user.uid)
    assert payload["login"] == LOGIN
    expected_exp = before + timedelta(minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    assert abs(payload["exp"] - expected_exp.timestamp()) < 5


def test_login_token_lifetime_comes_from_settings(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 7)
    _register(client)

    token = _login(client).json()["access_token"]

    payload = jwt.decode(token, options={"verify_signature": False})
    lifetime = payload["exp"] - datetime.now(tz=UTC).timestamp()
    assert 6 * 60 < lifetime <= 7 * 60


def test_login_with_wrong_password_returns_unauthorized(client: TestClient) -> None:
    _register(client)

    response = _login(client, password="wrong-password")

    assert response.status_code == 401
    assert response.json()["detail"] == "Неверное имя пользователя или пароль"


def test_login_of_unknown_user_returns_unauthorized(client: TestClient) -> None:
    response = _login(client, login="nobody")

    assert response.status_code == 401
    assert response.json()["detail"] == "Неверное имя пользователя или пароль"


# --- Проверка токена ---


def test_issued_token_is_accepted(client: TestClient, users_storage: dict[apps_types.UserUID, User]) -> None:
    _register(client)
    token = _login(client).json()["access_token"]

    response = _get_me(client, token)

    assert response.status_code == 200
    [user] = users_storage.values()
    assert response.json() == {"uid": str(user.uid), "login": LOGIN}


def test_token_signed_with_another_key_is_rejected(client: TestClient) -> None:
    foreign_private_pem = generate_rsa_pem_pair()[0]
    token = jwt.encode(_payload(), key=foreign_private_pem, algorithm="RS256")

    response = _get_me(client, token)

    assert response.status_code == 401
    assert response.json()["code"] == "FM-401000"


def test_token_signed_with_legacy_hardcoded_secret_is_rejected(client: TestClient) -> None:
    token = jwt.encode(_payload(), key="secret_key", algorithm="HS256")

    assert _get_me(client, token).status_code == 401


def test_unsigned_token_is_rejected(client: TestClient) -> None:
    token = jwt.encode(_payload(), key=None, algorithm="none")

    assert _get_me(client, token).status_code == 401


def test_expired_token_is_rejected(client: TestClient, signing_keys: tuple[bytes, bytes]) -> None:
    private_pem = signing_keys[0]
    token = jwt.encode(
        _payload(exp=datetime.now(tz=UTC) - timedelta(seconds=1)),
        key=private_pem,
        algorithm="RS256",
    )

    response = _get_me(client, token)

    assert response.status_code == 401
    assert response.json()["code"] == "FM-401000"


def test_token_without_exp_is_rejected(client: TestClient, signing_keys: tuple[bytes, bytes]) -> None:
    private_pem = signing_keys[0]
    token = jwt.encode(_payload(exp=None), key=private_pem, algorithm="RS256")

    assert _get_me(client, token).status_code == 401


def test_malformed_token_is_rejected(client: TestClient) -> None:
    assert _get_me(client, "not-a-jwt").status_code == 401


def test_request_without_token_is_rejected(client: TestClient) -> None:
    response = client.get("/test/me")

    assert response.status_code == 401
    assert response.json()["code"] == "FM-401000"
