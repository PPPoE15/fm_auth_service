from apps.modules.user.application.exceptions import CurrentUserNotFoundError
from apps.modules.user.application.uow import AbstractUserUnitOfWork
from apps.modules.user.domain import User
from apps.shared import apps_types


# NOTE(FM-15): обработчик запроса берёт AbstractUserUnitOfWork, как команды: отдельной read-модели пока нет.
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
