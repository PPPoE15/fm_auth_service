from typing import Annotated

from fastapi import APIRouter, Depends, status

from apps.config import app_settings
from apps.modules.session.api import deps, schemas
from apps.modules.session.application.tokens import TokenPair
from apps.web.security import UserInfo, get_user_info

# NOTE(FM-29): тег «Пользователь» у роутера сохранён, чтобы OpenAPI не изменился при разделении на модули:
# до переноса эндпоинты сессии жили в роутере пользователя и получали оба тега — «Пользователь» и «Сессия».
router = APIRouter(tags=["Пользователь"])


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


# TODO(FM-22): выход требует действующий access-токен (контракт). Если клиент на 401 обновит пару и повторит
# /logout со старым refresh, тот уже отозван ротацией — ответ 204, а новый refresh остаётся живым. Решение —
# выход только по refresh-токену (security: [] в контракте).
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
