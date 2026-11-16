from apps.modules.user.application.exceptions import CurrentUserNotFoundError
from apps.modules.user.application.uow import AbstractUserUnitOfWork
from apps.modules.user.domain import User
from apps.shared import apps_types
from apps.shared.logger import get_logger


class UpdateCurrentUserCommandHandler:
    """Обработчик команды изменения профиля текущего пользователя."""

    def __init__(self, unit_of_work: AbstractUserUnitOfWork) -> None:
        """
        Конструктор обработчика команды изменения профиля.

        Args:
            unit_of_work: Объект шаблона Единица работы.
        """
        self._uow = unit_of_work
        self._logger = get_logger()

    async def handle(self, uid: apps_types.UserUID, name: apps_types.UserName) -> User:
        """
        Задать имя текущему пользователю.

        Args:
            uid: Идентификатор пользователя (claim sub).
            name: Как обращаться к пользователю.

        Raises:
            CurrentUserNotFoundError: Если пользователя нет.
        """
        async with self._uow as uow:
            user = await uow.user_repo.get_by_uid(uid)
            # TODO(FM-38): загрузка «пользователь из токена или 401» и текст ошибки повторяют
            # GetCurrentUserQueryHandler; при следующем таком обработчике вынести в общий хелпер.
            if user is None:
                msg = "Не авторизованный запрос!"
                raise CurrentUserNotFoundError(msg)
            user.rename(name)
            await uow.user_repo.update(user)
            await uow.commit()
        self._logger.info("Изменён профиль пользователя %s", uid)
        return user
