from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import jwt

from apps.web.app.aggregators.models import RefreshToken, User
from apps.web.app.utils.datetime_tz import aware_now
from apps.web.security import generate_refresh_token, hash_refresh_token

from .uow import AbstractUserUnitOfWork


@dataclass(frozen=True)
class TokenPair:
    """Пара токенов сессии."""

    access_token: str
    refresh_token: str
    expires_in: int


class TokenIssuer:
    """Выдача пары access + refresh для пользователя."""

    def __init__(
        self,
        private_key: bytes,
        signing_algorithm: str,
        access_token_expire_minutes: int,
        refresh_token_expire_days: int,
    ) -> None:
        """
        Конструктор выдачи токенов.

        Args:
            private_key: Приватный ключ для подписания access-токена (PEM).
            signing_algorithm: Алгоритм подписания access-токена.
            access_token_expire_minutes: Время жизни access-токена в минутах.
            refresh_token_expire_days: Время жизни refresh-токена в днях.
        """
        self._private_key = private_key
        self._signing_algorithm = signing_algorithm
        self._access_token_lifetime = timedelta(minutes=access_token_expire_minutes)
        self._refresh_token_lifetime = timedelta(days=refresh_token_expire_days)

    async def issue(self, uow: AbstractUserUnitOfWork, user: User) -> TokenPair:
        """
        Выдать пару токенов и сохранить хеш refresh-токена. Фиксация транзакции — на вызывающем.

        Args:
            uow: Открытая единица работы.
            user: Пользователь, которому выдаются токены.
        """
        # TODO(FM-16): срок отсчитывается заново при каждой ротации — сессия без абсолютного предела живёт, пока
        # refresh вызывается хотя бы раз в REFRESH_TOKEN_EXPIRE_DAYS; переносить исходный срок цепочки или ограничить.
        now = aware_now()
        refresh_token = generate_refresh_token()
        await uow.refresh_token_repo.create(
            RefreshToken.create(
                user_uid=user.uid,
                token_hash=hash_refresh_token(refresh_token),
                expires_at=now + self._refresh_token_lifetime,
                created_date=now,
            ),
        )
        return TokenPair(
            access_token=self._create_access_token(user, now),
            refresh_token=refresh_token,
            expires_in=int(self._access_token_lifetime.total_seconds()),
        )

    def _create_access_token(self, user: User, now: datetime) -> str:
        """
        Создать JWT access-токен.

        Args:
            user: Сущность пользователя.
            now: Момент выдачи.
        """
        payload: dict[str, Any] = {
            "sub": str(user.uid),
            # NOTE(FM-15): claim login нужен только fm_transaction_service — его UserInfo требует это поле
            # до FM-9. Логин теперь — email. Сам сервис авторизации читает из токена только sub.
            "login": user.email,
            "exp": now + self._access_token_lifetime,
        }
        return jwt.encode(
            payload=payload,
            key=self._private_key,
            algorithm=self._signing_algorithm,
        )
