from sqlalchemy import select

from apps import db_models as orm_models
from apps.web.app.aggregators.models import RefreshToken
from apps.web.app.infrastructure.db.repos.base import BaseSqlAlchemyRepo

from . import builders
from .interface import RefreshTokenRepoInterface


# TODO(FM-16): отозванные и истёкшие строки не удаляются — каждый вход и refresh добавляет строку; нужна
# периодическая очистка (и индекс по expires_at).
class RefreshTokenRepo(RefreshTokenRepoInterface, BaseSqlAlchemyRepo):
    """Репозиторий refresh-токенов."""

    async def create(self, refresh_token: RefreshToken) -> None:
        self._session.add(builders.build_orm(refresh_token))
        await self._session.flush()

    async def get_by_hash_for_update(self, token_hash: str) -> RefreshToken | None:
        stmt = (
            select(orm_models.RefreshToken)
            .where(orm_models.RefreshToken.token_hash == token_hash)
            .with_for_update()
            # NOTE(FM-16): сейчас сессия на каждый UoW новая и populate_existing ничего не меняет; защита на случай,
            # если токен уже окажется в identity map — после ожидания блокировки нужна строка из БД, а не кэш.
            .execution_options(populate_existing=True)
        )
        orm_refresh_token = await self._session.scalar(stmt)
        return builders.build(orm_refresh_token) if orm_refresh_token else None

    # TODO(FM-16): merge делает лишний SELECT по uid (загруженный ORM-объект не удерживается сессией) — один
    # запрос на каждый refresh/logout; можно обновлять UPDATE ... WHERE uid или держать объект до update.
    async def update(self, refresh_token: RefreshToken) -> None:
        await self._session.merge(builders.build_orm(refresh_token))
        await self._session.flush()
