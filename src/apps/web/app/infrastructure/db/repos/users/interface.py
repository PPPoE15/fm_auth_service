import abc

from apps import apps_types
from apps.web.app.aggregators.models import User


class EmailAlreadyTakenError(Exception):
    """Email уже занят другим пользователем (нарушена уникальность в хранилище)."""


class UserRepoInterface(abc.ABC):
    """Интерфейс репозитория пользователей."""

    @abc.abstractmethod
    async def create(self, system_user: User) -> None:
        """
        Создать системного пользователя.

        Args:
            system_user: Модель системного пользователя.

        Raises:
            EmailAlreadyTakenError: Если пользователь с таким email уже есть.
        """

    @abc.abstractmethod
    async def update(self, system_user: User) -> None:
        """
        Обновить системного пользователя.

        Args:
            system_user: Модель системного пользователя.
        """

    @abc.abstractmethod
    async def get_by_email(self, email: apps_types.Email) -> User | None:
        """
        Получить пользователя по email.

        Args:
            email: Email пользователя (в нормализованном виде: нижний регистр, без пробелов по краям).
        """

    @abc.abstractmethod
    async def get_by_uid(self, uid: apps_types.UserUID) -> User | None:
        """
        Получить пользователя по UID

        Args:
            uid: UID пользователя.
        """

    @abc.abstractmethod
    async def delete(self, system_user: User) -> None:
        """
        Удаление записи пользователя.

        Args:
            system_user: Агрегатор пользователя.
        """
