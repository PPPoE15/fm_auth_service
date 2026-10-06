from datetime import timedelta
from typing import Any

import jwt

from apps import apps_types
from apps.web.app.aggregators.models import User
from apps.web.app.utils.datetime_tz import aware_now
from apps.web.logger import get_logger
from apps.web.security import dummy_password_hash, verify_password

from .exceptions import InvalidCredentialsError
from .uow import AbstractUserUnitOfWork


class AuthenticateCommandHandler:
    """Обработчик команды аутентификации."""

    def __init__(
        self,
        unit_of_work: AbstractUserUnitOfWork,
        private_key: bytes,
        token_expire_minutes: int,
        signing_algorithm: str,
    ) -> None:
        """
        Конструктор обработчика команды Аутентификации PAM.

        Args:
            unit_of_work: Объект шаблона Единица работы.
            private_key: Приватный ключ для подписания токена (PEM).
            token_expire_minutes: Время жизни токена в минутах.
            signing_algorithm: Алгоритм подписания токена.
        """
        self._uow = unit_of_work
        self._private_key = private_key
        self._token_expire_minutes = token_expire_minutes
        self._signing_algorithm = signing_algorithm
        self._logger = get_logger()

    async def handle(
        self,
        email: apps_types.Email,
        password: apps_types.Password,
    ) -> str:
        """
        Аутентифицировать и создать JWT-токен.

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
        # TODO(FM-001.11): argon2 (64 МиБ, time_cost=3) считается синхронно и блокирует event loop, теперь и для
        # неизвестных email; вынести в поток (anyio.to_thread.run_sync) и добавить rate limit на /token.
        if not verify_password(password, password_hash) or user is None:
            msg = "Неверный email или пароль"
            raise InvalidCredentialsError(msg)

        return self._create_access_token(user)

    def _create_access_token(self, user: User) -> str:
        """
        Создать JWT-токен.

        Args:
            user: Сущность пользователя.
        """
        expire = aware_now() + timedelta(minutes=self._token_expire_minutes)
        payload: dict[str, Any] = {
            "sub": str(user.uid),
            # NOTE(FM-001.7): claim login нужен только fm_transaction_service — его UserInfo требует это поле
            # до FM-001.2. Логин теперь — email. Сам сервис авторизации читает из токена только sub.
            "login": user.email,
            "exp": expire,
        }
        self._logger.info("Авторизован пользователь %s", user.uid)
        return jwt.encode(
            payload=payload,
            key=self._private_key,
            algorithm=self._signing_algorithm,
        )
