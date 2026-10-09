from apps.modules.session.application.ports import RefreshTokenRepoInterface
from apps.modules.user import UserRepoInterface
from apps.shared.unit_of_work import AbstractUnitOfWork


class AbstractSessionUnitOfWork(AbstractUnitOfWork):
    """Абстрактная единица работы для сессий (refresh-токенов) пользователя."""

    # Пользователь нужен в той же транзакции, что и токены: вход и refresh выдают токены по его данным.
    user_repo: UserRepoInterface
    refresh_token_repo: RefreshTokenRepoInterface
