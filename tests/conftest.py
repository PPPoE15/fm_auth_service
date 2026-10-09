import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Настройки БД обязательны при импорте apps.config, а сама БД в тестах не используется.
for _name, _value in {
    "DB_HOST": "localhost",
    "DB_PORT": "5432",
    "DB_DATABASE": "test",
    "DB_USER": "test",
    "DB_PASSWORD": "test",
}.items():
    os.environ.setdefault(_name, _value)

from fastapi import Depends, FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from apps.config import app_settings  # noqa: E402
from apps.modules.session.api import deps as session_deps  # noqa: E402
from apps.modules.user.api import deps as user_deps  # noqa: E402
from apps.web.main import build_app  # noqa: E402
from apps.web.security import UserInfo, get_user_info  # noqa: E402
from tests.modules.session.fakes import InMemorySessionUnitOfWork, RefreshTokensStorage  # noqa: E402
from tests.modules.user.fakes import InMemoryUserUnitOfWork, UsersStorage  # noqa: E402


def generate_rsa_pem_pair() -> tuple[bytes, bytes]:
    """Сгенерировать пару RSA-ключей в формате PEM (приватный, публичный)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


@pytest.fixture(scope="session")
def rsa_key_pair() -> tuple[bytes, bytes]:
    """Пара ключей подписи JWT, общая для всех тестов."""
    return generate_rsa_pem_pair()


@pytest.fixture(autouse=True)
def signing_keys(
    rsa_key_pair: tuple[bytes, bytes],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[bytes, bytes]:
    """Подложить сервису файлы ключей подписи из временного каталога."""
    private_pem, public_pem = rsa_key_pair
    private_path = tmp_path / "jwt_private.pem"
    public_path = tmp_path / "jwt_public.pem"
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)
    monkeypatch.setattr(app_settings, "PRIVATE_KEY_PATH", str(private_path))
    monkeypatch.setattr(app_settings, "PUBLIC_KEY_PATH", str(public_path))
    monkeypatch.setattr(app_settings, "TOKEN_SIGNING_ALGORITHM", "RS256")
    return rsa_key_pair


@pytest.fixture
def users_storage() -> UsersStorage:
    """Хранилище пользователей одного теста."""
    return {}


@pytest.fixture
def refresh_tokens_storage() -> RefreshTokensStorage:
    """Хранилище refresh-токенов одного теста."""
    return {}


@pytest.fixture
def uow(
    users_storage: UsersStorage,
    refresh_tokens_storage: RefreshTokensStorage,
) -> InMemorySessionUnitOfWork:
    """Единица работы в памяти (модуля сессии — она видит и пользователей, и refresh-токены)."""
    return InMemorySessionUnitOfWork(users_storage, refresh_tokens_storage)


@pytest.fixture
def app(
    users_storage: UsersStorage,
    refresh_tokens_storage: RefreshTokensStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> FastAPI:
    """Приложение сервиса с хранилищами в памяти и тестовым защищённым эндпоинтом."""
    # Модули пользователя и сессии работают с одним хранилищем пользователей, как с одной таблицей users.
    monkeypatch.setattr(user_deps, "UserUnitOfWork", lambda **_: InMemoryUserUnitOfWork(users_storage))
    monkeypatch.setattr(
        session_deps,
        "SessionUnitOfWork",
        lambda **_: InMemorySessionUnitOfWork(users_storage, refresh_tokens_storage),
    )
    fastapi_app = build_app()

    @fastapi_app.get("/test/protected")
    async def protected(user_info: UserInfo = Depends(get_user_info)) -> dict[str, Any]:
        return {"uid": str(user_info.uid)}

    return fastapi_app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
