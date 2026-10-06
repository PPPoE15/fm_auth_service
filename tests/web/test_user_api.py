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

NAME = "Артём"
EMAIL = "name@example.com"
PASSWORD = "s3cret-Passw0rd"


@pytest.fixture
def app(users_storage: dict[apps_types.UserUID, User], monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """Приложение сервиса с хранилищем пользователей в памяти и тестовым защищённым эндпоинтом."""
    monkeypatch.setattr(deps, "UserUnitOfWork", lambda **_: InMemoryUserUnitOfWork(users_storage))
    fastapi_app = build_app()

    @fastapi_app.get("/test/protected")
    async def protected(user_info: UserInfo = Depends(get_user_info)) -> dict[str, Any]:
        return {"uid": str(user_info.uid)}

    return fastapi_app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _registration_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": NAME,
        "email": EMAIL,
        "password": PASSWORD,
        "password_confirmation": PASSWORD,
    }
    body.update(overrides)
    return body


def _register(client: TestClient, **overrides: Any) -> Response:
    return client.post("/auth/registration", json=_registration_body(**overrides))


def _login(client: TestClient, email: str = EMAIL, password: str = PASSWORD) -> Response:
    return client.post("/auth/token", json={"email": email, "password": password})


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "sub": "6f9619ff-8b86-4011-b42d-00c04fc964ff",
        "exp": datetime.now(tz=UTC) + timedelta(minutes=5),
    }
    payload.update(overrides)
    return {key: value for key, value in payload.items() if value is not None}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _get_protected(client: TestClient, token: str) -> Response:
    return client.get("/test/protected", headers=_auth(token))


def _validation_fields(response: Response) -> set[str]:
    return {item["field"] for item in response.json()["validation"]}


# --- Регистрация ---


def test_registration_returns_created_user(client: TestClient, users_storage: dict[apps_types.UserUID, User]) -> None:
    response = _register(client)

    assert response.status_code == 201
    [user] = users_storage.values()
    assert response.json() == {"uid": str(user.uid), "name": NAME, "email": EMAIL}
    assert user.name == NAME
    assert user.email == EMAIL
    assert user.password_hash != PASSWORD


def test_registration_normalizes_name_and_email(client: TestClient) -> None:
    response = _register(client, name="  Артём  ", email="  Name@Example.COM ")

    assert response.status_code == 201
    assert response.json()["name"] == "Артём"
    assert response.json()["email"] == "name@example.com"


def test_registration_allows_same_name_for_different_emails(client: TestClient) -> None:
    assert _register(client).status_code == 201

    assert _register(client, email="other@example.com").status_code == 201


def test_registration_of_taken_email_returns_conflict(client: TestClient) -> None:
    assert _register(client).status_code == 201

    response = _register(client, name="Другой", email="NAME@example.com")

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "FM-409001"
    assert body["status"] == 409
    assert "уже существует" in body["detail"]
    assert body["instance"] == "/auth/registration"
    assert response.headers["content-type"] == "application/problem+json"


def test_registration_race_on_unique_email_returns_conflict(
    client: TestClient,
    users_storage: dict[apps_types.UserUID, User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверка «email свободен» прошла, но параллельная регистрация успела раньше — уникальный индекс."""
    assert _register(client).status_code == 201

    async def email_is_free(*_: Any) -> None:
        return None

    monkeypatch.setattr("tests.conftest.InMemoryUserRepo.get_by_email", email_is_free)

    response = _register(client)

    assert response.status_code == 409
    assert response.json()["code"] == "FM-409001"
    assert len(users_storage) == 1


def test_registration_with_mismatched_passwords_returns_bad_request(client: TestClient) -> None:
    response = _register(client, password_confirmation="other-Passw0rd")

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "FM-400001"
    assert body["detail"] == "Пароли не совпадают"
    assert body["validation"] == [
        {
            "message": "Пароли не совпадают",
            "field": "password_confirmation",
            "rejectedValue": None,
            "rule": "value_error",
        },
    ]


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"name": ""}, "name"),
        ({"name": "   "}, "name"),
        ({"name": "Ар\x00тём"}, "name"),
        ({"name": "Ар\ttём"}, "name"),
        ({"name": "я" * 65}, "name"),
        ({"email": "not-an-email"}, "email"),
        ({"email": "a@"}, "email"),
        ({"email": "two@at@example.com"}, "email"),
        ({"email": "a\x00b@example.com"}, "email"),
        ({"email": "a\x7fb@example.com"}, "email"),
        ({"email": "a" * 245 + "@example.com"}, "email"),
        ({"password": "short", "password_confirmation": "short"}, "password"),
        ({"password": "x" * 129, "password_confirmation": "x" * 129}, "password"),
    ],
)
def test_registration_rejects_invalid_fields(client: TestClient, overrides: dict[str, Any], field: str) -> None:
    response = _register(client, **overrides)

    assert response.status_code == 422
    assert response.json()["code"] == "FM-422000"
    assert field in _validation_fields(response)


def test_registration_accepts_boundary_lengths(client: TestClient) -> None:
    response = _register(client, name="я" * 64, password="x" * 8, password_confirmation="x" * 8)

    assert response.status_code == 201


@pytest.mark.parametrize("missing", ["name", "email", "password", "password_confirmation"])
def test_registration_requires_all_fields(client: TestClient, missing: str) -> None:
    body = _registration_body()
    del body[missing]

    response = client.post("/auth/registration", json=body)

    assert response.status_code == 422
    assert missing in _validation_fields(response)


def test_registration_rejects_unknown_fields(client: TestClient) -> None:
    response = _register(client, login="artem")

    assert response.status_code == 422
    assert "login" in _validation_fields(response)


def test_validation_error_never_echoes_passwords(client: TestClient) -> None:
    response = _register(client, password="Qz7#k", password_confirmation="Wq9#m")

    assert response.status_code == 422
    password_items = [item for item in response.json()["validation"] if item["field"].startswith("password")]
    assert {item["field"] for item in password_items} == {"password", "password_confirmation"}
    assert all(item["rejectedValue"] is None for item in password_items)
    assert "Qz7#k" not in response.text
    assert "Wq9#m" not in response.text


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
    expected_exp = before + timedelta(minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    assert abs(payload["exp"] - expected_exp.timestamp()) < 5


def test_login_token_keeps_login_claim_for_transaction_service(client: TestClient) -> None:
    """fm_transaction_service до FM-001.2 требует claim login."""
    _register(client)

    token = _login(client).json()["access_token"]

    assert jwt.decode(token, options={"verify_signature": False})["login"] == EMAIL


def test_login_token_lifetime_comes_from_settings(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 7)
    _register(client)

    token = _login(client).json()["access_token"]

    payload = jwt.decode(token, options={"verify_signature": False})
    lifetime = payload["exp"] - datetime.now(tz=UTC).timestamp()
    assert 6 * 60 < lifetime <= 7 * 60


def test_login_email_is_case_insensitive(client: TestClient) -> None:
    _register(client)

    assert _login(client, email=" NAME@Example.com ").status_code == 200


@pytest.mark.parametrize(
    ("email", "password"),
    [
        (EMAIL, "wrong-Passw0rd"),
        ("nobody@example.com", PASSWORD),
    ],
)
def test_login_with_wrong_credentials_returns_same_unauthorized(client: TestClient, email: str, password: str) -> None:
    _register(client)

    response = _login(client, email=email, password=password)

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "FM-401001"
    assert body["detail"] == "Неверный email или пароль"


def test_login_by_old_login_field_is_rejected(client: TestClient) -> None:
    _register(client)

    response = client.post("/auth/token", json={"login": EMAIL, "password": PASSWORD})

    assert response.status_code == 422


def test_login_validates_fields(client: TestClient) -> None:
    response = _login(client, email="not-an-email", password="short")

    assert response.status_code == 422
    assert _validation_fields(response) == {"email", "password"}


# --- Текущий пользователь ---


def test_me_returns_current_user(client: TestClient, users_storage: dict[apps_types.UserUID, User]) -> None:
    _register(client)
    token = _login(client).json()["access_token"]

    response = client.get("/auth/me", headers=_auth(token))

    assert response.status_code == 200
    [user] = users_storage.values()
    assert response.json() == {"uid": str(user.uid), "name": NAME, "email": EMAIL}


def test_me_without_token_is_rejected(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "FM-401000"


def test_me_with_invalid_token_is_rejected(client: TestClient) -> None:
    response = client.get("/auth/me", headers=_auth("not-a-jwt"))

    assert response.status_code == 401
    assert response.json()["code"] == "FM-401000"


def test_me_with_expired_token_is_rejected(
    client: TestClient,
    users_storage: dict[apps_types.UserUID, User],
    signing_keys: tuple[bytes, bytes],
) -> None:
    _register(client)
    [user] = users_storage.values()
    token = jwt.encode(
        _payload(sub=str(user.uid), exp=datetime.now(tz=UTC) - timedelta(seconds=1)),
        key=signing_keys[0],
        algorithm="RS256",
    )

    response = client.get("/auth/me", headers=_auth(token))

    assert response.status_code == 401
    assert response.json()["code"] == "FM-401000"


def test_me_of_deleted_user_is_rejected(client: TestClient, users_storage: dict[apps_types.UserUID, User]) -> None:
    _register(client)
    token = _login(client).json()["access_token"]
    users_storage.clear()

    response = client.get("/auth/me", headers=_auth(token))

    assert response.status_code == 401
    assert response.json()["code"] == "FM-401000"


# --- Проверка токена ---


def test_issued_token_is_accepted(client: TestClient, users_storage: dict[apps_types.UserUID, User]) -> None:
    _register(client)
    token = _login(client).json()["access_token"]

    response = _get_protected(client, token)

    assert response.status_code == 200
    [user] = users_storage.values()
    assert response.json() == {"uid": str(user.uid)}


def test_token_signed_with_another_key_is_rejected(client: TestClient) -> None:
    foreign_private_pem = generate_rsa_pem_pair()[0]
    token = jwt.encode(_payload(), key=foreign_private_pem, algorithm="RS256")

    response = _get_protected(client, token)

    assert response.status_code == 401
    assert response.json()["code"] == "FM-401000"


def test_token_signed_with_legacy_hardcoded_secret_is_rejected(client: TestClient) -> None:
    token = jwt.encode(_payload(), key="secret_key", algorithm="HS256")

    assert _get_protected(client, token).status_code == 401


def test_unsigned_token_is_rejected(client: TestClient) -> None:
    token = jwt.encode(_payload(), key=None, algorithm="none")

    assert _get_protected(client, token).status_code == 401


def test_expired_token_is_rejected(client: TestClient, signing_keys: tuple[bytes, bytes]) -> None:
    private_pem = signing_keys[0]
    token = jwt.encode(
        _payload(exp=datetime.now(tz=UTC) - timedelta(seconds=1)),
        key=private_pem,
        algorithm="RS256",
    )

    response = _get_protected(client, token)

    assert response.status_code == 401
    assert response.json()["code"] == "FM-401000"


def test_token_without_exp_is_rejected(client: TestClient, signing_keys: tuple[bytes, bytes]) -> None:
    private_pem = signing_keys[0]
    token = jwt.encode(_payload(exp=None), key=private_pem, algorithm="RS256")

    assert _get_protected(client, token).status_code == 401


def test_malformed_token_is_rejected(client: TestClient) -> None:
    assert _get_protected(client, "not-a-jwt").status_code == 401


def test_request_without_token_is_rejected(client: TestClient) -> None:
    response = client.get("/test/protected")

    assert response.status_code == 401
    assert response.json()["code"] == "FM-401000"
