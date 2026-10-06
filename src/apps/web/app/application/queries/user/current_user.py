from apps import apps_types
from apps.web.app.aggregators.models import User
from apps.web.app.application.commands.user.uow import AbstractUserUnitOfWork
from apps.web.app.utils.exceptions import BaseUnauthorizedError


class CurrentUserNotFoundError(BaseUnauthorizedError):
    """Пользователь из действительного токена не найден (например, удалён)."""


class GetCurrentUserQueryHandler:
    """Обработчик запроса данных текущего пользователя."""

    def __init__(self, unit_of_work: AbstractUserUnitOfWork) -> None:
        """
        Конструктор обработчика запроса текущего пользователя.

        Args:
            unit_of_work: Объект шаблона Единица работы.
        """
        self._uow = unit_of_work

    async def handle(self, uid: apps_types.UserUID) -> User:
        """
        Получить пользователя по идентификатору из токена.

        Args:
            uid: Идентификатор пользователя (claim sub).

        Raises:
            CurrentUserNotFoundError: Если пользователя нет.
        """
        async with self._uow as uow:
            user = await uow.user_repo.get_by_uid(uid)
        if user is None:
            msg = "Не авторизованный запрос!"
            raise CurrentUserNotFoundError(msg)
        return user
