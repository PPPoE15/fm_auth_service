from pydantic import BaseModel, Field

from apps import apps_types
from apps.utils.schemas import Base


class CreateUserSchema(Base):
    """Схема данных для создания пользователя"""

    login: apps_types.UserLogin = Field(
        description="Имя пользователя",
    )
    password: apps_types.Password = Field(
        description="Пароль.",
    )
    password_confirmation: apps_types.Password = Field(
        description="Повторение пароля.",
    )
    email: apps_types.Email | None = Field(
        description="Email пользователя",
    )


class AuthorizationSchema(Base):
    """Схема данных для авторизации"""

    login: apps_types.UserLogin | apps_types.Email = Field(
        description="Имя пользователя или e-mail",
    )
    password: apps_types.Password = Field(
        description="Пароль",
    )


class TokenSchema(BaseModel):
    """JWT-токен"""

    access_token: str = Field(title="JWT-токен", description="JWT-токен для доступа к API")
    token_type: str = Field(
        title="Тип JWT-токена",
        description="Тип JWT-токена для доступа к API",
        max_length=256,
        examples=["bearer"],
    )
