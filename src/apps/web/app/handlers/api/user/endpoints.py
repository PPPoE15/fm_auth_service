from fastapi import APIRouter

from apps import apps_types

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
