from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from apps import apps_types
from apps import db_models as orm_models
from apps.web.app.aggregators.models import User
from apps.web.app.infrastructure.db.repos.base import BaseSqlAlchemyRepo

from . import builders
from .interface import EmailAlreadyTakenError, UserRepoInterface

_EMAIL_UNIQUE_CONSTRAINT = "uq_users_email"


class UserRepo(UserRepoInterface, BaseSqlAlchemyRepo):
    """Репозиторий пользователей."""

    async def create(self, system_user: User) -> None:
        orm_system_user = builders.build_orm(system_user)
        self._session.add(orm_system_user)
        # flush сразу, чтобы нарушение уникальности email проявилось здесь, а не на commit.
        try:
            await self._session.flush()
        except IntegrityError as exc:
            if _EMAIL_UNIQUE_CONSTRAINT in str(exc.orig):
                raise EmailAlreadyTakenError from exc
            raise

    async def update(self, system_user: User) -> None:
        orm_system_user = builders.build_orm(system_user)
        orm_system_user = await self._session.merge(orm_system_user)

    async def get_by_email(self, email: apps_types.Email) -> User | None:
        stmt = select(orm_models.User).where(orm_models.User.email == email)
        orm_user = await self._session.scalar(stmt)
        return builders.build(orm_user) if orm_user else None

    async def get_by_uid(self, uid: apps_types.UserUID) -> User | None:
        stmt = select(orm_models.User).where(orm_models.User.uid == uid)
        orm_user = await self._session.scalar(stmt)
        return builders.build(orm_user) if orm_user else None

    async def delete(self, system_user: User) -> None:
        orm_system_user = await self._session.get(orm_models.User, system_user.uid)
        await self._session.delete(orm_system_user)
