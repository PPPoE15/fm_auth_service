from pydantic import Field

from apps import apps_types
from apps.utils.schemas import Base


class CreateUserSchema(Base):
    """Схема данных для создания пол"""

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
