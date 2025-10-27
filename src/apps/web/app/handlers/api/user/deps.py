from apps.web.app.application.commands.user import CreateUserCommandHandler, UserUnitOfWork
from apps.web.app.handlers.deps import async_session_factory


def build_user_create_command_handler() -> CreateUserCommandHandler:
    """Построить обработчик создания пользователя."""
    return CreateUserCommandHandler(unit_of_work=UserUnitOfWork(session_factory=async_session_factory))
