"""
Реестр ORM-моделей всех модулей.

Импортирует `infrastructure/orm.py` каждого модуля, чтобы все таблицы были в `AsyncBase.metadata`
(Alembic) и внешние ключи между таблицами разных модулей (`refresh_tokens.user_uid` -> `users.uid`) разрешались.
"""

from apps.modules.session.infrastructure.orm import RefreshToken
from apps.modules.user.infrastructure.orm import User
from apps.shared.db.base import AsyncBase

__all__ = [
    "AsyncBase",
    "RefreshToken",
    "User",
]
