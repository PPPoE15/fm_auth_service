import os
from pathlib import Path
from typing import Any, Self

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
from apps.web.app.aggregators.models import User  # noqa: E402
from apps.web.app.application.commands.user.uow import AbstractUserUnitOfWork  # noqa: E402
from apps.web.app.infrastructure.db.repos.users import UserRepoInterface  # noqa: E402


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
        self._storage[system_user.uid] = system_user

    async def update(self, system_user: User) -> None:
        self._storage[system_user.uid] = system_user

    async def get_by_login(self, login: apps_types.UserLogin) -> User | None:
        return next((user for user in self._storage.values() if user.login == login), None)

    async def get_by_uid(self, uid: apps_types.UserUID) -> User | None:
        return self._storage.get(uid)

    async def delete(self, system_user: User) -> None:
        self._storage.pop(system_user.uid, None)


class InMemoryUserUnitOfWork(AbstractUserUnitOfWork):
    """Единица работы поверх общего хранилища в памяти (изменения видны сразу)."""

    def __init__(self, storage: dict[apps_types.UserUID, User], **_: Any) -> None:
        self._storage = storage
        self.committed = False

    async def __aenter__(self) -> Self:
        self.user_repo = InMemoryUserRepo(self._storage)
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
def uow(users_storage: dict[apps_types.UserUID, User]) -> InMemoryUserUnitOfWork:
    """Единица работы в памяти."""
    return InMemoryUserUnitOfWork(users_storage)
