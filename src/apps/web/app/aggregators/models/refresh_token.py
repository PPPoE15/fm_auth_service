from datetime import datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import Field

from apps import apps_types
from apps.utils.schemas import Base


class RefreshToken(Base):
    """Агрегатор refresh-токена. Открытое значение токена не хранится — только его хеш."""

    uid: UUID = Field(
        description="Уникальный ID записи refresh-токена.",
    )
    user_uid: apps_types.UserUID = Field(
        description="Пользователь, которому выдан токен.",
    )
    token_hash: str = Field(
        description="Хеш открытого значения токена (SHA-256, hex).",
    )
    expires_at: datetime = Field(
        description="Момент, после которого токен недействителен.",
    )
    revoked: bool = Field(
        default=False,
        description="Токен отозван (использован при ротации или при выходе).",
    )
    created_date: datetime = Field(
        description="Дата выдачи токена.",
    )

    @classmethod
    def create(
        cls,
        user_uid: apps_types.UserUID,
        token_hash: str,
        expires_at: datetime,
        created_date: datetime,
    ) -> Self:
        """
        Создать запись о выданном refresh-токене.

        Args:
            user_uid: Пользователь, которому выдан токен.
            token_hash: Хеш открытого значения токена.
            expires_at: Момент истечения срока действия.
            created_date: Дата выдачи.
        """
        return cls(
            uid=uuid4(),
            user_uid=user_uid,
            token_hash=token_hash,
            expires_at=expires_at,
            created_date=created_date,
        )

    def is_active(self, now: datetime) -> bool:
        """
        Токен действителен: не отозван и срок действия не истёк.

        Args:
            now: Текущий момент.
        """
        return not self.revoked and now < self.expires_at

    def belongs_to(self, user_uid: apps_types.UserUID) -> bool:
        """
        Токен выдан этому пользователю.

        Args:
            user_uid: Идентификатор пользователя.
        """
        return self.user_uid == user_uid

    def revoke(self) -> None:
        """Отозвать токен (идемпотентно)."""
        self.revoked = True
