from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UUID, String

from apps import apps_types
from apps.db_models.base import AsyncBase
from apps.db_models.utils.tz_type import TZDateTime


class User(AsyncBase):
    """Сущность пользователя."""

    __tablename__ = "users"

    uid: Mapped[apps_types.UserUID] = mapped_column(
        UUID,
        primary_key=True,
        doc="Уникальный ID записи пользователя.",
    )
    name: Mapped[apps_types.UserName] = mapped_column(
        String(64),
        doc="Как обращаться к пользователю (не уникально).",
    )
    password_hash: Mapped[apps_types.PasswordHash] = mapped_column(
        String,
        doc="Хэш пароля.",
    )
    # NOTE(FM-001.7): uq_users_email чувствителен к регистру — нижний регистр обеспечивает только HTTP-схема
    # (EmailField). Новый путь записи в обход неё должен нормализовать email сам (или нужен индекс по lower(email)).
    email: Mapped[apps_types.Email] = mapped_column(
        String(254),
        doc="Email пользователя в нижнем регистре (уникален, используется для входа).",
        unique=True,
    )
    created_date: Mapped[datetime] = mapped_column(
        TZDateTime,
        doc="Дата создания записи объекта",
    )
