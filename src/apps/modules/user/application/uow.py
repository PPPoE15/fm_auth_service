from apps.modules.user.application.ports import UserRepoInterface
from apps.shared.unit_of_work import AbstractUnitOfWork


class AbstractUserUnitOfWork(AbstractUnitOfWork):
    """Абстрактная единица работы для пользователя."""

    user_repo: UserRepoInterface
