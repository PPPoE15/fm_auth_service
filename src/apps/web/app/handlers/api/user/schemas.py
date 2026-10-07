import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from apps import apps_types
from apps.utils.schemas import Base

# NOTE(FM-15): по контракту отклоняются только C0 и DEL; C1 (U+0080–U+009F), U+2028/2029 и bidi-override
# (U+202E) в name проходят — при необходимости ужесточить вместе с контрактом.
# Управляющие \t, \n, \r по краям name срезаются strip_whitespace до проверки, а не отклоняются — так
# читается «пробелы по краям обрезаются до проверки» из контракта.
_CONTROL_CHARS = re.compile(r"[\x00-\x1F\x7F]")


def _reject_control_chars(value: str) -> str:
    """Отклонить строку с управляющими символами."""
    if _CONTROL_CHARS.search(value):
        msg = "Строка не должна содержать управляющие символы"
        raise ValueError(msg)
    return value


_EMAIL_MAX_LENGTH = 254


# NOTE(FM-15): превышение длины после lower() отдаёт rule value_error, а не string_too_long, как обычная
# проверка длины; если клиенту понадобится сопоставлять по rule — бросать PydanticCustomError("string_too_long").
def _check_email_length(value: str) -> str:
    """
    Проверить длину email после нормализации.

    max_length в StringConstraints проверяется до to_lower, а lower() может удлинить строку
    (например, «İ» → «i̇», два символа), и email не влез бы в колонку varchar(254).
    """
    if len(value) > _EMAIL_MAX_LENGTH:
        msg = f"Email не должен быть длиннее {_EMAIL_MAX_LENGTH} символов"
        raise ValueError(msg)
    return value


# Ограничения полей — по contracts/auth.openapi.yaml (UserName, Email, Password).
# «Не только пробелы» обеспечивается обрезкой пробелов до проверки min_length.
UserNameField = Annotated[
    apps_types.UserName,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=64),
    AfterValidator(_reject_control_chars),
]
# TODO(FM-15): невидимые символы (U+200B–U+200F, U+202A–U+202E, U+2060, U+FEFF) и разная Unicode-нормализация
# (NFC/NFD) дают внешне одинаковые, но разные email; отклонять их и делать NFC перед lower().
EmailField = Annotated[
    apps_types.Email,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=3,
        max_length=_EMAIL_MAX_LENGTH,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
    AfterValidator(_reject_control_chars),
    AfterValidator(_check_email_length),
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


class RefreshRequestSchema(RequestBase):
    """Refresh-токен для обновления сессии или выхода."""

    refresh_token: str = Field(
        min_length=1,
        max_length=512,
        description="Непрозрачный refresh-токен из POST /token или POST /token/refresh.",
    )


class TokenSchema(BaseModel):
    """Пара токенов сессии."""

    access_token: str = Field(title="JWT-токен", description="JWT для заголовка Authorization в обоих сервисах.")
    refresh_token: str = Field(
        title="Refresh-токен",
        description="Непрозрачный токен для POST /token/refresh и POST /logout.",
    )
    token_type: str = Field(
        title="Тип JWT-токена",
        description="Тип JWT-токена для доступа к API",
        max_length=256,
        examples=["bearer"],
    )
    expires_in: int = Field(
        title="Время жизни access-токена",
        description="Время жизни access-токена в секундах.",
        ge=1,
        examples=[900],
    )
