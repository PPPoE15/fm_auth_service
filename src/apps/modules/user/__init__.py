"""Публичный API модуля пользователя: другие модули импортируют из `user` только отсюда."""

# NOTE(FM-29): как и в fm_transaction_service (FM-30), API смешивает домен/порты и инфраструктуру: `UserRepo` нужен
# единице работы модуля session, поэтому импорт `UserRepoInterface` загружает и ORM пользователя.

from apps.modules.user.application.ports import UserRepoInterface
from apps.modules.user.domain import EmailField, PasswordField, User
from apps.modules.user.infrastructure.repo import UserRepo

__all__ = [
    "EmailField",
    "PasswordField",
    "User",
    "UserRepo",
    "UserRepoInterface",
]
