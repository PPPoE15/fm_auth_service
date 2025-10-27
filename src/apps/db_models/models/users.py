from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UUID, String

from apps import apps_types
from apps.db_models.base import AsyncBase


class User(AsyncBase):
    """Сущность пользователя."""

    __tablename__ = "users"

    uid: Mapped[apps_types.UserUID] = mapped_column(
        UUID,
        primary_key=True,
        doc="Уникальный ID записи пользователя.",
    )
    login: Mapped[apps_types.UserLogin] = mapped_column(
        String,
        doc="Имя пользователя",
    )
    password_hash: Mapped[apps_types.PasswordHash] = mapped_column(
        String,
        doc="Хэш пароля.",
    )
    email: Mapped[apps_types.Email | None] = mapped_column(
        String,
        doc="Email пользователя",
        nullable=True,
    )
    created_date: Mapped[datetime] = mapped_column(
        DateTime,
        doc="Дата создания записи объекта",
    )
