from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from apps import apps_types
from apps.config import app_settings

from . import deps, schemas

router = APIRouter(tags=["Пользователь"])


@router.post(
    "/registration",
    summary="Регистрация пользователя",
    description="Создать учетную запись пользователя",
)
async def create_user(
    item_in: schemas.CreateUserSchema,
) -> apps_types.UserUID:
    """
    Создать пользователя.

    Args:
        item_in: Информация о транзакции.
    """
    command_handler = deps.build_user_create_command_handler()
    return await command_handler.handle(
        login=item_in.login,
        password=item_in.password,
        password_confirmation=item_in.password_confirmation,
        email=item_in.email,
    )


@router.post(
    "/token",
)
async def token_route_handler(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> schemas.TokenSchema:
    """
    JWT-токен пользователя.

    Args:
        form_data: форма аутентификации пользователя.
    """
    command_handler = deps.build_user_auth_command_handler()
    access_token = await command_handler.handle(form_data.username, form_data.password)
    return schemas.TokenSchema(
        access_token=access_token,
        token_type=app_settings.TOKEN_TYPE,
    )
