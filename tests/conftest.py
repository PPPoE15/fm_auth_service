import os
from datetime import datetime
from pathlib import Path
from typing import Any, Self
from uuid import UUID

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

from apps import apps_types  # noqa: E402
from apps.config import app_settings  # noqa: E402
from apps.web.app.aggregators.models import RefreshToken, User  # noqa: E402
from apps.web.app.application.commands.user.uow import AbstractUserUnitOfWork  # noqa: E402
from apps.web.app.infrastructure.db.repos.refresh_tokens import RefreshTokenRepoInterface  # noqa: E402
from apps.web.app.infrastructure.db.repos.users import EmailAlreadyTakenError, UserRepoInterface  # noqa: E402

RefreshTokensStorage = dict[UUID, RefreshToken]


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


class InMemoryUserRepo(UserRepoInterface):
    """Репозиторий пользователей в памяти."""

    def __init__(self, storage: dict[apps_types.UserUID, User]) -> None:
        self._storage = storage

    async def create(self, system_user: User) -> None:
        # Как уникальный индекс users.email в БД.
        if any(user.email == system_user.email for user in self._storage.values()):
            raise EmailAlreadyTakenError
        self._storage[system_user.uid] = system_user

    async def update(self, system_user: User) -> None:
        self._storage[system_user.uid] = system_user

    async def get_by_email(self, email: apps_types.Email) -> User | None:
        return next((user for user in self._storage.values() if user.email == email), None)

    async def get_by_uid(self, uid: apps_types.UserUID) -> User | None:
        return self._storage.get(uid)

    async def delete(self, system_user: User) -> None:
        self._storage.pop(system_user.uid, None)


class InMemoryRefreshTokenRepo(RefreshTokenRepoInterface):
    """Репозиторий refresh-токенов в памяти."""

    def __init__(self, storage: RefreshTokensStorage) -> None:
        self._storage = storage

    async def create(self, refresh_token: RefreshToken) -> None:
        self._storage[refresh_token.uid] = refresh_token

    async def revoke_active(self, token_hash: str, now: datetime) -> RefreshToken | None:
        for uid, token in self._storage.items():
            if token.token_hash == token_hash and not token.revoked and token.expires_at > now:
                self._storage[uid] = token.model_copy(update={"revoked": True})
                return self._storage[uid]
        return None

    async def revoke(self, token_hash: str, user_uid: apps_types.UserUID) -> None:
        for uid, token in self._storage.items():
            if token.token_hash == token_hash and token.user_uid == user_uid:
                self._storage[uid] = token.model_copy(update={"revoked": True})


class InMemoryUserUnitOfWork(AbstractUserUnitOfWork):
    """Единица работы поверх общего хранилища в памяти (изменения видны сразу)."""

    def __init__(
        self,
        storage: dict[apps_types.UserUID, User],
        refresh_tokens_storage: RefreshTokensStorage | None = None,
        **_: Any,
    ) -> None:
        self._storage = storage
        self._refresh_tokens_storage = {} if refresh_tokens_storage is None else refresh_tokens_storage
        self.committed = False

    async def __aenter__(self) -> Self:
        self.user_repo = InMemoryUserRepo(self._storage)
        self.refresh_token_repo = InMemoryRefreshTokenRepo(self._refresh_tokens_storage)
        return self

    async def rollback(self) -> None:
        """Откат в памяти не нужен."""

    async def commit(self) -> None:
        self.committed = True


@pytest.fixture
def users_storage() -> dict[apps_types.UserUID, User]:
    """Хранилище пользователей одного теста."""
    return {}


@pytest.fixture
def refresh_tokens_storage() -> RefreshTokensStorage:
    """Хранилище refresh-токенов одного теста."""
    return {}


@pytest.fixture
def uow(
    users_storage: dict[apps_types.UserUID, User],
    refresh_tokens_storage: RefreshTokensStorage,
) -> InMemoryUserUnitOfWork:
    """Единица работы в памяти."""
    return InMemoryUserUnitOfWork(users_storage, refresh_tokens_storage)
