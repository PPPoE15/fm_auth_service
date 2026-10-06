from datetime import datetime
from uuid import UUID as PyUUID  # noqa: N811

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UUID, String

from apps import apps_types
from apps.db_models.base import AsyncBase
from apps.db_models.utils.tz_type import TZDateTime


class RefreshToken(AsyncBase):
    """Выданный refresh-токен. Открытое значение не хранится — только его хеш."""

    __tablename__ = "refresh_tokens"

    uid: Mapped[PyUUID] = mapped_column(
        UUID,
        primary_key=True,
        doc="Уникальный ID записи refresh-токена.",
    )
    user_uid: Mapped[apps_types.UserUID] = mapped_column(
        UUID,
        ForeignKey("users.uid", ondelete="CASCADE"),
        index=True,
        doc="Пользователь, которому выдан токен.",
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        doc="SHA-256 (hex) открытого значения токена.",
    )
    expires_at: Mapped[datetime] = mapped_column(
        TZDateTime,
        doc="Момент, после которого токен недействителен.",
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        doc="Токен отозван (использован при ротации или при выходе).",
    )
    created_date: Mapped[datetime] = mapped_column(
        TZDateTime,
        doc="Дата выдачи токена.",
    )
