from typing import Any, Self

from apps.modules.session.application.uow import AbstractSessionUnitOfWork
from apps.modules.session.infrastructure.repo import RefreshTokenRepo
from apps.modules.user import UserRepo
from apps.shared.unit_of_work import AbstractSQLAlchemyUnitOfWork


class SessionUnitOfWork(AbstractSessionUnitOfWork, AbstractSQLAlchemyUnitOfWork):
    """Единица работы для пользователя и его сессий."""

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Инициализация единицы работы для сессий.

        Args:
            *args: Позиционные аргументы.
            **kwargs: Именованные аргументы.
        """
        super().__init__(*args, **kwargs)

    async def __aenter__(self) -> Self:
        """Зайти в асинхронный контекстный менеджер."""
        self._session = self._session_factory()
        self.user_repo = UserRepo(self._session)
        self.refresh_token_repo = RefreshTokenRepo(self._session)
        return self
