from typing import Annotated

from fastapi import APIRouter, Depends, status

from apps.config import app_settings
from apps.web.security import UserInfo, get_user_info

from . import deps, schemas

router = APIRouter(tags=["Пользователь"])


@router.post(
    "/registration",
    summary="Регистрация пользователя",
    description="Создать учетную запись пользователя",
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    item_in: schemas.CreateUserSchema,
) -> schemas.UserSchema:
    """
    Создать пользователя.

    Args:
        item_in: Данные регистрации.
    """
    command_handler = deps.build_user_create_command_handler()
    user = await command_handler.handle(
        name=item_in.name,
        email=item_in.email,
        password=item_in.password,
        password_confirmation=item_in.password_confirmation,
    )
    return schemas.UserSchema.model_validate(user)


@router.post(
    "/token",
    summary="Вход в аккаунт",
)
async def token_route_handler(
    form_data: schemas.AuthorizationSchema,
) -> schemas.TokenSchema:
    """
    JWT-токен пользователя.

    Args:
        form_data: форма аутентификации пользователя.
    """
    command_handler = deps.build_user_auth_command_handler()
    access_token = await command_handler.handle(form_data.email, form_data.password)
    return schemas.TokenSchema(
        access_token=access_token,
        token_type=app_settings.TOKEN_TYPE,
    )


@router.get(
    "/me",
    summary="Текущий пользователь",
    description="Имя для приветствия и блока пользователя в боковом меню.",
)
async def get_current_user(
    user_info: Annotated[UserInfo, Depends(get_user_info)],
) -> schemas.UserSchema:
    """
    Данные текущего пользователя.

    Args:
        user_info: Информация о пользователе из токена.
    """
    query_handler = deps.build_current_user_query_handler()
    user = await query_handler.handle(user_info.uid)
    return schemas.UserSchema.model_validate(user)
