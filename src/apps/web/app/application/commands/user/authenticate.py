from apps import apps_types
from apps.web.logger import get_logger
from apps.web.security import dummy_password_hash, verify_password

from .exceptions import InvalidCredentialsError
from .tokens import TokenIssuer, TokenPair
from .uow import AbstractUserUnitOfWork


class AuthenticateCommandHandler:
    """Обработчик команды аутентификации."""

    def __init__(
        self,
        unit_of_work: AbstractUserUnitOfWork,
        token_issuer: TokenIssuer,
    ) -> None:
        """
        Конструктор обработчика команды Аутентификации PAM.

        Args:
            unit_of_work: Объект шаблона Единица работы.
            token_issuer: Выдача пары токенов.
        """
        self._uow = unit_of_work
        self._token_issuer = token_issuer
        self._logger = get_logger()

    async def handle(
        self,
        email: apps_types.Email,
        password: apps_types.Password,
    ) -> TokenPair:
        """
        Аутентифицировать и выдать пару токенов.

        Args:
            email: Email пользователя (нормализованный: нижний регистр, без пробелов по краям).
            password: Пароль пользователя.

        Raises:
            InvalidCredentialsError: Если email или пароль неверны (какое из двух — не раскрывается).
        """
        async with self._uow as uow:
            user = await uow.user_repo.get_by_email(email)
        # Для неизвестного email пароль всё равно проверяется (по фиктивному хешу), чтобы время ответа
        # не выдавало, зарегистрирован ли email.
        password_hash = user.password_hash if user else dummy_password_hash()
        # TODO(FM-20): argon2 (64 МиБ, time_cost=3) считается синхронно и блокирует event loop, теперь и для
        # неизвестных email; вынести в поток (anyio.to_thread.run_sync) и добавить rate limit на /token.
        if not verify_password(password, password_hash) or user is None:
            msg = "Неверный email или пароль"
            raise InvalidCredentialsError(msg)

        # Проверка пароля — вне транзакции, чтобы не держать соединение из пула на время argon2.
        async with self._uow as uow:
            token_pair = await self._token_issuer.issue(uow, user)
            await uow.commit()
        self._logger.info("Авторизован пользователь %s", user.uid)
        return token_pair
