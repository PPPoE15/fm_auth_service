from typing import Any, Self

from apps.web.app.application.commands.unit_of_work import AbstractSQLAlchemyUnitOfWork, AbstractUnitOfWork
from apps.web.app.infrastructure.db.repos.refresh_tokens import RefreshTokenRepo, RefreshTokenRepoInterface
from apps.web.app.infrastructure.db.repos.users import UserRepo, UserRepoInterface


class AbstractUserUnitOfWork(AbstractUnitOfWork):
    """Абстрактная единица работы для пользователя и его сессий (refresh-токенов)."""

    user_repo: UserRepoInterface
    refresh_token_repo: RefreshTokenRepoInterface


class UserUnitOfWork(AbstractUserUnitOfWork, AbstractSQLAlchemyUnitOfWork):
    """Единица работы для пользователя и его транзакций."""

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
        self.refresh_token_repo = RefreshTokenRepo(self._session)
        return self
