from datetime import datetime

from sqlalchemy import update

from apps import apps_types
from apps import db_models as orm_models
from apps.web.app.aggregators.models import RefreshToken
from apps.web.app.infrastructure.db.repos.base import BaseSqlAlchemyRepo

from . import builders
from .interface import RefreshTokenRepoInterface


class RefreshTokenRepo(RefreshTokenRepoInterface, BaseSqlAlchemyRepo):
    """Репозиторий refresh-токенов."""

    async def create(self, refresh_token: RefreshToken) -> None:
        self._session.add(builders.build_orm(refresh_token))
        await self._session.flush()

    async def revoke_active(self, token_hash: str, now: datetime) -> RefreshToken | None:
        # Один UPDATE ... RETURNING: строка блокируется, и параллельный запрос с тем же токеном,
        # дождавшись блокировки, уже не пройдёт условие revoked = false.
        stmt = (
            update(orm_models.RefreshToken)
            .where(
                orm_models.RefreshToken.token_hash == token_hash,
                orm_models.RefreshToken.revoked.is_(False),
                orm_models.RefreshToken.expires_at > now,
            )
            .values(revoked=True)
            .returning(orm_models.RefreshToken)
            .execution_options(synchronize_session=False)
        )
        orm_refresh_token = await self._session.scalar(stmt)
        return builders.build(orm_refresh_token) if orm_refresh_token else None

    async def revoke(self, token_hash: str, user_uid: apps_types.UserUID) -> None:
        stmt = (
            update(orm_models.RefreshToken)
            .where(
                orm_models.RefreshToken.token_hash == token_hash,
                orm_models.RefreshToken.user_uid == user_uid,
            )
            .values(revoked=True)
            .execution_options(synchronize_session=False)
        )
        await self._session.execute(stmt)
