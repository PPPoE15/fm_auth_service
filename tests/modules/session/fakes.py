"""Фейки модуля сессии: refresh-токены в памяти и единица работы поверх хранилищ пользователей и токенов."""

from typing import Any, Self
from uuid import UUID

from apps.modules.session.application.ports import RefreshTokenRepoInterface
from apps.modules.session.application.uow import AbstractSessionUnitOfWork
from apps.modules.session.domain import RefreshToken
from tests.modules.user.fakes import InMemoryUserRepo, UsersStorage

RefreshTokensStorage = dict[UUID, RefreshToken]


# NOTE(FM-16): блокировка (FOR UPDATE) не моделируется — «из параллельных refresh проходит один» тестами не
# покрыто; это проверяется вручную на Postgres (см. «Adapters stay thin» в CLAUDE.md).
class InMemoryRefreshTokenRepo(RefreshTokenRepoInterface):
    """Репозиторий refresh-токенов в памяти."""

    def __init__(self, storage: RefreshTokensStorage) -> None:
        self._storage = storage

    async def create(self, refresh_token: RefreshToken) -> None:
        self._storage[refresh_token.uid] = refresh_token.model_copy()

    async def get_by_hash_for_update(self, token_hash: str) -> RefreshToken | None:
        token = next((token for token in self._storage.values() if token.token_hash == token_hash), None)
        # Копия, как строка из БД: изменения агрегата попадают в хранилище только через update.
        return token.model_copy() if token else None

    async def update(self, refresh_token: RefreshToken) -> None:
        self._storage[refresh_token.uid] = refresh_token.model_copy()


# NOTE(FM-16): изменения применяются сразу и rollback их не отменяет, в отличие от Postgres: после ошибки внутри
# UoW (например, refresh удалённого пользователя) состояние хранилища не совпадает с продовым.
class InMemorySessionUnitOfWork(AbstractSessionUnitOfWork):
    """Единица работы модуля сессии поверх общих хранилищ в памяти (изменения видны сразу)."""

    def __init__(
        self,
        storage: UsersStorage,
        refresh_tokens_storage: RefreshTokensStorage | None = None,
        **_: Any,
    ) -> None:
        self._storage = storage
        self._refresh_tokens_storage = {} if refresh_tokens_storage is None else refresh_tokens_storage
        self.committed = False

    async def __aenter__(self) -> Self:
        self.user_repo = InMemoryUserRepo(self._storage)
        self.refresh_token_repo = InMemoryRefreshTokenRepo(self._refresh_tokens_storage)
        return self

    async def rollback(self) -> None:
        """Откат в памяти не нужен."""

    async def commit(self) -> None:
        self.committed = True
