from pydantic import BaseModel, Field

from apps.modules.user import EmailField, PasswordField
from apps.shared.api_schemas import RequestBase


class AuthorizationSchema(RequestBase):
    """Схема данных для авторизации"""

    email: EmailField = Field(
        description="Email пользователя",
    )
    password: PasswordField = Field(
        description="Пароль",
    )


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
