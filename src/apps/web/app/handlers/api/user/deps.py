from apps.config import app_settings
from apps.web.app.application.commands.user import AuthenticateCommandHandler, CreateUserCommandHandler, UserUnitOfWork
from apps.web.app.handlers.deps import async_session_factory
from apps.web.security import load_private_key


def build_user_create_command_handler() -> CreateUserCommandHandler:
    """Построить обработчик создания пользователя."""
    return CreateUserCommandHandler(unit_of_work=UserUnitOfWork(session_factory=async_session_factory))


def build_user_auth_command_handler() -> AuthenticateCommandHandler:
    """Построить обработчик авторизации пользователя."""
    return AuthenticateCommandHandler(
        unit_of_work=UserUnitOfWork(session_factory=async_session_factory),
        private_key=load_private_key(),
        token_expire_minutes=app_settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        signing_algorithm=app_settings.TOKEN_SIGNING_ALGORITHM,
    )
