from typing import Annotated

from fastapi import APIRouter, Depends, status

from apps.modules.user.api import deps, schemas
from apps.web.security import UserInfo, get_user_info

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
