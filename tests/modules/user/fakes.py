"""Фейки модуля пользователя: хранилище в памяти и единица работы поверх него."""

from typing import Any, Self

from apps.modules.user.application.ports import EmailAlreadyTakenError, UserRepoInterface
from apps.modules.user.application.uow import AbstractUserUnitOfWork
from apps.modules.user.domain import User
from apps.shared import apps_types

UsersStorage = dict[apps_types.UserUID, User]


class InMemoryUserRepo(UserRepoInterface):
    """Репозиторий пользователей в памяти."""

    def __init__(self, storage: UsersStorage) -> None:
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


class InMemoryUserUnitOfWork(AbstractUserUnitOfWork):
    """Единица работы модуля пользователя поверх общего хранилища в памяти (изменения видны сразу)."""

    def __init__(self, storage: UsersStorage, **_: Any) -> None:
        self._storage = storage
        self.committed = False

    async def __aenter__(self) -> Self:
        self.user_repo = InMemoryUserRepo(self._storage)
        return self

    async def rollback(self) -> None:
        """Откат в памяти не нужен."""

    async def commit(self) -> None:
        self.committed = True
