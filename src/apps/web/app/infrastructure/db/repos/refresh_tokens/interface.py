import abc

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
    async def get_by_hash_for_update(self, token_hash: str) -> RefreshToken | None:
        """
        Получить токен по хешу, заблокировав его до конца транзакции.

        Блокировка нужна для ротации: параллельный запрос с тем же токеном ждёт её снятия и видит токен
        уже отозванным, поэтому из нескольких одновременных обновлений успешно только одно.

        Args:
            token_hash: Хеш открытого значения токена.
        """

    @abc.abstractmethod
    async def update(self, refresh_token: RefreshToken) -> None:
        """
        Сохранить изменения токена.

        Args:
            refresh_token: Агрегатор refresh-токена.
        """
