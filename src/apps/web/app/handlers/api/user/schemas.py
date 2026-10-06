import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from apps import apps_types
from apps.utils.schemas import Base

_CONTROL_CHARS = re.compile(r"[\x00-\x1F\x7F]")


def _reject_control_chars(value: str) -> str:
    """Отклонить строку с управляющими символами."""
    if _CONTROL_CHARS.search(value):
        msg = "Строка не должна содержать управляющие символы"
        raise ValueError(msg)
    return value


# Ограничения полей — по contracts/auth.openapi.yaml (UserName, Email, Password).
# «Не только пробелы» обеспечивается обрезкой пробелов до проверки min_length.
UserNameField = Annotated[
    apps_types.UserName,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=64),
    AfterValidator(_reject_control_chars),
]
EmailField = Annotated[
    apps_types.Email,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
    AfterValidator(_reject_control_chars),
]
PasswordField = Annotated[apps_types.Password, StringConstraints(min_length=8, max_length=128)]


class RequestBase(Base):
    """База схем тела запроса: неизвестные поля отклоняются (422)."""

    model_config = ConfigDict(extra="forbid")


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


class AuthorizationSchema(RequestBase):
    """Схема данных для авторизации"""

    email: EmailField = Field(
        description="Email пользователя",
    )
    password: PasswordField = Field(
        description="Пароль",
    )


class UserSchema(Base):
    """Данные пользователя."""

    uid: apps_types.UserUID = Field(description="Идентификатор пользователя.")
    name: apps_types.UserName = Field(description="Как обращаться к пользователю.")
    email: apps_types.Email = Field(description="Email пользователя.")


class TokenSchema(BaseModel):
    """JWT-токен"""

    access_token: str = Field(title="JWT-токен", description="JWT-токен для доступа к API")
    token_type: str = Field(
        title="Тип JWT-токена",
        description="Тип JWT-токена для доступа к API",
        max_length=256,
        examples=["bearer"],
    )
