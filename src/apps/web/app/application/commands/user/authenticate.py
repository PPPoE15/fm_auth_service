from datetime import timedelta
from typing import Any

import jwt

from apps import apps_types
from apps.web.app.aggregators.models import User
from apps.web.app.utils.datetime_tz import aware_now
from apps.web.security import verify_password

from .exceptions import UnauthorizedError
from .uow import AbstractUserUnitOfWork


class AuthenticateCommandHandler:
    """Обработчик команды аутентификации."""

    def __init__(
        self,
        unit_of_work: AbstractUserUnitOfWork,
        private_key: str,
        token_expire_minutes: int,
        signing_algorithm: str,
    ) -> None:
        """
        Конструктор обработчика команды Аутентификации PAM.

        Args:
            unit_of_work: Объект шаблона Единица работы.
            private_key: Приватный ключ для подписания токена.
            token_expire_minutes: Время жизни токена в минутах.
            signing_algorithm: Алгоритм подписания токена.
        """
        self._uow = unit_of_work
        self._private_key = private_key
        self._token_expire_minutes = token_expire_minutes
        self._signing_algorithm = signing_algorithm

    async def handle(
        self,
        login: apps_types.UserLogin,
        password: apps_types.Password,
    ) -> str:
        """
        Аутентифицировать и создать JWT-токен.

        Args:
            login: Логин пользователя.
            password: Пароль пользователя.
        """
        async with self._uow as uow:
            user = await uow.user_repo.get_by_login(login)
            if not user:
                msg = "Неверное имя пользователя или пароль"
                raise UnauthorizedError(msg)
            if not verify_password(password, user.password_hash):
                msg = "Неверное имя пользователя или пароль"
                raise UnauthorizedError(msg)

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
            "login": user.login,
            "exp": expire,
        }

        return jwt.encode(
            payload=payload,
            key="secret_key",
            # key=self._private_key,
            # algorithm=self._signing_algorithm,
        )
