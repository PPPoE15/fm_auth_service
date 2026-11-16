from pydantic import Field, field_validator

from apps.modules.user.domain import EmailField, PasswordField, UserNameField
from apps.shared import apps_types
from apps.shared.api_schemas import RequestBase
from apps.shared.schemas import Base


class CreateUserSchema(RequestBase):
    """Схема данных для создания пользователя"""

    name: UserNameField | None = Field(
        default=None,
        description="Как обращаться к пользователю (не уникально). Необязательно: задаётся позже через PATCH /me.",
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

    # NOTE(FM-38): из-за `| None` сгенерированный /openapi.json описывает name как anyOf string/null, хотя явный
    # null отклоняется (контракт: необязательная строка, не nullable). Клиенты пишутся по контракту из fm-auto-dev.
    @field_validator("name", mode="before")
    @classmethod
    def _reject_explicit_null(cls, value: object) -> object:
        """По контракту name либо не передаётся, либо строка: явный null отклоняется."""
        if value is None:
            msg = "Имя не может быть null"
            raise ValueError(msg)
        return value


class UpdateCurrentUserSchema(RequestBase):
    """Схема изменения профиля текущего пользователя."""

    name: UserNameField = Field(
        description="Как обращаться к пользователю (не уникально).",
    )


class UserSchema(Base):
    """Данные пользователя."""

    uid: apps_types.UserUID = Field(description="Идентификатор пользователя.")
    name: apps_types.UserName | None = Field(
        description="Как обращаться к пользователю; null — имя ещё не задано (окно «Первый шаг» не пройдено).",
    )
    email: apps_types.Email = Field(description="Email пользователя.")
