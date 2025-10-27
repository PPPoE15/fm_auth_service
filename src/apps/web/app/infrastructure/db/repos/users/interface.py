import abc

from apps import apps_types
from apps.web.app.aggregators.models import User


class UserRepoInterface(abc.ABC):
    """Интерфейс репозитория пользователей."""

    @abc.abstractmethod
    async def create(self, system_user: User) -> None:
        """
        Создать системного пользователя.

        Args:
            system_user: Модель системного пользователя.
        """

    @abc.abstractmethod
    async def update(self, system_user: User) -> None:
        """
        Обновить системного пользователя.

        Args:
            system_user: Модель системного пользователя.
        """

    @abc.abstractmethod
    async def get_by_login(self, login: apps_types.UserLogin) -> User | None:
        """
        Получить пользователя по его логину

        Args:
            login: Логин пользователя
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
