from typing import Annotated

from fastapi import APIRouter, Depends, status

from apps.config import app_settings
from apps.web.app.application.commands.user import TokenPair
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


def _token_response(token_pair: TokenPair) -> schemas.TokenSchema:
    """Ответ с парой токенов."""
    return schemas.TokenSchema(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=app_settings.TOKEN_TYPE,
        expires_in=token_pair.expires_in,
    )


@router.post(
    "/token",
    summary="Вход в аккаунт",
    description="Выдаёт пару access/refresh-токенов.",
    tags=["Сессия"],
)
async def token_route_handler(
    form_data: schemas.AuthorizationSchema,
) -> schemas.TokenSchema:
    """
    Пара токенов пользователя.

    Args:
        form_data: форма аутентификации пользователя.
    """
    command_handler = deps.build_user_auth_command_handler()
    return _token_response(await command_handler.handle(form_data.email, form_data.password))


@router.post(
    "/token/refresh",
    summary="Обновление токенов",
    description="Обменивает действующий refresh-токен на новую пару; переданный refresh-токен отзывается.",
    tags=["Сессия"],
)
async def refresh_token_route_handler(
    item_in: schemas.RefreshRequestSchema,
) -> schemas.TokenSchema:
    """
    Новая пара токенов по refresh-токену.

    Args:
        item_in: Refresh-токен.
    """
    command_handler = deps.build_refresh_token_command_handler()
    return _token_response(await command_handler.handle(item_in.refresh_token))


# NOTE(FM-17): выход требует действующий access-токен (контракт). Если клиент на 401 обновит пару и повторит
# /logout со старым refresh, тот уже отозван ротацией — ответ 204, а новый refresh остаётся живым. При повторе
# клиент должен подставлять в тело новый refresh-токен.
@router.post(
    "/logout",
    summary="Выход",
    description=(
        "Отзывает переданный refresh-токен. Access-токен остаётся действительным до истечения срока. "
        "Повторный вызов с уже отозванным токеном также возвращает 204."
    ),
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Сессия"],
)
async def logout(
    item_in: schemas.RefreshRequestSchema,
    user_info: Annotated[UserInfo, Depends(get_user_info)],
) -> None:
    """
    Завершить сессию.

    Args:
        item_in: Refresh-токен сессии.
        user_info: Информация о пользователе из access-токена.
    """
    command_handler = deps.build_logout_command_handler()
    await command_handler.handle(user_info.uid, item_in.refresh_token)


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
