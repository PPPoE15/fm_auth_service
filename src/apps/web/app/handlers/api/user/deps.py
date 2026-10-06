from apps.config import app_settings
from apps.web.app.application.commands.user import (
    AuthenticateCommandHandler,
    CreateUserCommandHandler,
    LogoutCommandHandler,
    RefreshTokenCommandHandler,
    TokenIssuer,
    UserUnitOfWork,
)
from apps.web.app.application.queries.user import GetCurrentUserQueryHandler
from apps.web.app.handlers.deps import async_session_factory
from apps.web.security import load_private_key


def build_user_create_command_handler() -> CreateUserCommandHandler:
    """Построить обработчик создания пользователя."""
    return CreateUserCommandHandler(unit_of_work=UserUnitOfWork(session_factory=async_session_factory))


def build_token_issuer() -> TokenIssuer:
    """Построить выдачу пары токенов по настройкам."""
    return TokenIssuer(
        private_key=load_private_key(),
        signing_algorithm=app_settings.TOKEN_SIGNING_ALGORITHM,
        access_token_expire_minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days=app_settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )


def build_user_auth_command_handler() -> AuthenticateCommandHandler:
    """Построить обработчик авторизации пользователя."""
    return AuthenticateCommandHandler(
        unit_of_work=UserUnitOfWork(session_factory=async_session_factory),
        token_issuer=build_token_issuer(),
    )


def build_refresh_token_command_handler() -> RefreshTokenCommandHandler:
    """Построить обработчик обновления пары токенов."""
    return RefreshTokenCommandHandler(
        unit_of_work=UserUnitOfWork(session_factory=async_session_factory),
        token_issuer=build_token_issuer(),
    )


def build_logout_command_handler() -> LogoutCommandHandler:
    """Построить обработчик выхода."""
    return LogoutCommandHandler(unit_of_work=UserUnitOfWork(session_factory=async_session_factory))


def build_current_user_query_handler() -> GetCurrentUserQueryHandler:
    """Построить обработчик запроса текущего пользователя."""
    return GetCurrentUserQueryHandler(unit_of_work=UserUnitOfWork(session_factory=async_session_factory))
