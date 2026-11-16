from apps.modules.user.application.commands import CreateUserCommandHandler, UpdateCurrentUserCommandHandler
from apps.modules.user.application.queries import GetCurrentUserQueryHandler
from apps.modules.user.infrastructure.uow import UserUnitOfWork
from apps.shared.db.session import async_session_factory


def build_user_create_command_handler() -> CreateUserCommandHandler:
    """Построить обработчик создания пользователя."""
    return CreateUserCommandHandler(unit_of_work=UserUnitOfWork(session_factory=async_session_factory))


def build_current_user_query_handler() -> GetCurrentUserQueryHandler:
    """Построить обработчик запроса текущего пользователя."""
    return GetCurrentUserQueryHandler(unit_of_work=UserUnitOfWork(session_factory=async_session_factory))


def build_update_current_user_command_handler() -> UpdateCurrentUserCommandHandler:
    """Построить обработчик изменения профиля текущего пользователя."""
    return UpdateCurrentUserCommandHandler(unit_of_work=UserUnitOfWork(session_factory=async_session_factory))
