from apps import apps_types
from apps.web.app.aggregators.models import User
from apps.web.app.infrastructure.db.repos.users import EmailAlreadyTakenError
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
        name: apps_types.UserName,
        email: apps_types.Email,
        password: apps_types.Password,
        password_confirmation: apps_types.Password,
    ) -> User:
        """
        Создать пользователя.

        Args:
            name: Как обращаться к пользователю.
            email: Email пользователя (нормализованный: нижний регистр, без пробелов по краям).
            password: Пароль.
            password_confirmation: Подтверждение пароля.

        Raises:
            PasswordConfirmationError: Если пароль и подтверждение не совпадают.
            UserAlreadyExistsError: Если пользователь с таким email уже есть.
        """
        if password != password_confirmation:
            msg = "Пароли не совпадают"
            raise exceptions.PasswordConfirmationError(msg)

        already_exists_msg = f'Пользователь с email "{email}" уже существует.'
        async with self._uow as uow:
            if await uow.user_repo.get_by_email(email):
                raise exceptions.UserAlreadyExistsError(already_exists_msg)

            # TODO(FM-20): argon2 считается при открытой транзакции и занятом соединении из пула; при выносе
            # хеширования в поток (см. TODO в authenticate.py) хешировать до входа в UoW.
            user_agg = User.create(
                name=name,
                password_hash=hash_password(password),
                email=email,
                created_date=aware_now(),
            )
            try:
                await uow.user_repo.create(user_agg)
            except EmailAlreadyTakenError:
                # Параллельная регистрация с тем же email успела раньше — сработал уникальный индекс.
                raise exceptions.UserAlreadyExistsError(already_exists_msg) from None
            await uow.commit()
        self._logger.info("Зарегистрирован пользователь %s", user_agg.uid)
        return user_agg
