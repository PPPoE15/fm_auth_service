from datetime import datetime
from typing import Self
from uuid import uuid4

from pydantic import Field

from apps import apps_types
from apps.utils.schemas import Base


class User(Base):
    """Агрегатор пользователя."""

    uid: apps_types.UserUID = Field(
        description="Уникальный ID записи пользователя.",
    )
    login: apps_types.UserLogin = Field(
        description="Имя пользователя",
    )
    password_hash: apps_types.PasswordHash = Field(
        description="Хэш пароля.",
    )
    email: apps_types.Email | None = Field(
        description="Email пользователя",
    )
    created_date: datetime = Field(
        title="Created Date",
        description="Дата создания записи пользователем",
        examples=["2023-08-02T08:25:20.918267"],
    )

    @classmethod
    def create(
        cls,
        login: apps_types.UserLogin,
        password_hash: apps_types.PasswordHash,
        email: apps_types.Email | None,
        created_date: datetime,
    ) -> Self:
        """
        Создать пользователя.

        Args:
            login: Имя пользователя.
            password_hash: Хэш пароля.
            email: Email пользователя.
            created_date: Дата создания пользователя.
        """
        user_uid = uuid4()
        return cls(
            uid=user_uid,
            login=login,
            password_hash=password_hash,
            email=email,
            created_date=created_date,
        )
