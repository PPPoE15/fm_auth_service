from datetime import datetime
from typing import Self
from uuid import uuid4

from pydantic import Field

from apps.shared import apps_types
from apps.shared.schemas import Base


class User(Base):
    """Агрегатор пользователя."""

    uid: apps_types.UserUID = Field(
        description="Уникальный ID записи пользователя.",
    )
    name: apps_types.UserName | None = Field(
        description="Как обращаться к пользователю (не уникально); None — имя ещё не задано.",
    )
    password_hash: apps_types.PasswordHash = Field(
        description="Хэш пароля.",
    )
    email: apps_types.Email = Field(
        description="Email пользователя (уникален, используется для входа).",
    )
    created_date: datetime = Field(
        title="Created Date",
        description="Дата создания записи пользователем",
        examples=["2023-08-02T08:25:20.918267"],
    )

    @classmethod
    def create(
        cls,
        name: apps_types.UserName | None,
        password_hash: apps_types.PasswordHash,
        email: apps_types.Email,
        created_date: datetime,
    ) -> Self:
        """
        Создать пользователя.

        Args:
            name: Как обращаться к пользователю; None — имя не задано при регистрации.
            password_hash: Хэш пароля.
            email: Email пользователя.
            created_date: Дата создания пользователя.
        """
        user_uid = uuid4()
        return cls(
            uid=user_uid,
            name=name,
            password_hash=password_hash,
            email=email,
            created_date=created_date,
        )

    # TODO(FM-38): правила имени (обрезка, 1–64 символа, без управляющих символов, не None) проверяет только
    # API-схема (UserNameField); у Base нет validate_assignment. Перенести проверку в агрегат, когда появится
    # второй путь записи имени (как и для User.create).
    def rename(self, name: apps_types.UserName) -> None:
        """
        Задать или сменить имя пользователя.

        Сбросить имя обратно в None нельзя: после окна «Первый шаг» оно всегда задано.

        Args:
            name: Как обращаться к пользователю.
        """
        self.name = name
