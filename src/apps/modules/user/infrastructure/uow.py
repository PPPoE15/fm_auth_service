from typing import Any, Self

from apps.modules.user.application.uow import AbstractUserUnitOfWork
from apps.modules.user.infrastructure.repo import UserRepo
from apps.shared.unit_of_work import AbstractSQLAlchemyUnitOfWork


class UserUnitOfWork(AbstractUserUnitOfWork, AbstractSQLAlchemyUnitOfWork):
    """Единица работы для пользователя."""

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Инициализация единицы работы для пользователя.

        Args:
            *args: Позиционные аргументы.
            **kwargs: Именованные аргументы.
        """
        super().__init__(*args, **kwargs)

    async def __aenter__(self) -> Self:
        """Зайти в асинхронный контекстный менеджер."""
        self._session = self._session_factory()
        self.user_repo = UserRepo(self._session)
        return self
