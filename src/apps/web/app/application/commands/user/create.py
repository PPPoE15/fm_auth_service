from apps import apps_types
from apps.web.app.aggregators.models import User
from apps.web.app.utils.datetime_tz import aware_now
from apps.web.logger import get_logger
from apps.web.security import hash_password

from . import exceptions
from .uow import AbstractUserUnitOfWork


class CreateUserCommandHandler:
    """Класс обработчика команды создания пользователя."""

    def __init__(
        self,
        unit_of_work: AbstractUserUnitOfWork,
    ) -> None:
        """
        Конструктор обработчика команды создания пользователя.

        Args:
            unit_of_work: Объект шаблона Единица работы.
        """
        self._uow = unit_of_work
        self._logger = get_logger()

    async def handle(
        self,
        login: apps_types.UserLogin,
        password: apps_types.Password,
        password_confirmation: apps_types.Password,
        email: apps_types.Email | None,
    ) -> apps_types.UserUID:
        """
        Создать пользователя.

        Args:
            login: Имя пользователя.
            password: Пароль.
            password_confirmation: Подтверждение пароля.
            email: Email пользователя.
        """
        if password != password_confirmation:
            msg = "Пароли не совпадают"
            raise exceptions.PasswordConfirmationError(msg)

        async with self._uow as uow:
            user_agg = await uow.user_repo.get_by_login(login)
            if user_agg:
                msg = f'Пользователь с логином "{login}" уже существует.'
                raise exceptions.UserAlreadyExistsError(msg)

            user_agg = User.create(
                login=login,
                password_hash=hash_password(password),
                email=email,
                created_date=aware_now(),
            )
            await uow.user_repo.create(user_agg)
            await uow.commit()
            msg = f"Зарегистрирован пользователь {user_agg.login}"
        self._logger.info(msg)
        return user_agg.uid
