import abc
from datetime import datetime

from apps import apps_types
from apps.web.app.aggregators.models import RefreshToken


class RefreshTokenRepoInterface(abc.ABC):
    """Интерфейс репозитория refresh-токенов."""

    @abc.abstractmethod
    async def create(self, refresh_token: RefreshToken) -> None:
        """
        Сохранить выданный refresh-токен.

        Args:
            refresh_token: Агрегатор refresh-токена.
        """

    @abc.abstractmethod
    async def revoke_active(self, token_hash: str, now: datetime) -> RefreshToken | None:
        """
        Атомарно отозвать действующий токен (не отозван и не истёк) и вернуть его (уже отозванным).

        Атомарность нужна для ротации: из двух параллельных запросов с одним токеном успешен только один.

        Args:
            token_hash: Хеш открытого значения токена.
            now: Текущий момент, с которым сравнивается срок действия.

        Returns:
            Отозванный токен или None, если действующего токена с таким хешем нет.
        """

    @abc.abstractmethod
    async def revoke(self, token_hash: str, user_uid: apps_types.UserUID) -> None:
        """
        Отозвать токен пользователя (идемпотентно: отозванный, истёкший или чужой токен — не ошибка).

        Args:
            token_hash: Хеш открытого значения токена.
            user_uid: Владелец токена; токен другого пользователя не отзывается.
        """
