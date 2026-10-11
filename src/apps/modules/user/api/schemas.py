from pydantic import Field

from apps.modules.user.domain import EmailField, PasswordField, UserNameField
from apps.shared import apps_types
from apps.shared.api_schemas import RequestBase
from apps.shared.schemas import Base


class CreateUserSchema(RequestBase):
    """Схема данных для создания пользователя"""

    name: UserNameField = Field(
        description="Как обращаться к пользователю (не уникально).",
    )
    email: EmailField = Field(
        description="Email пользователя, используется для входа.",
    )
    password: PasswordField = Field(
        description="Пароль.",
    )
    password_confirmation: PasswordField = Field(
        description="Повторение пароля.",
    )


class UserSchema(Base):
    """Данные пользователя."""

    uid: apps_types.UserUID = Field(description="Идентификатор пользователя.")
    name: apps_types.UserName = Field(description="Как обращаться к пользователю.")
    email: apps_types.Email = Field(description="Email пользователя.")
