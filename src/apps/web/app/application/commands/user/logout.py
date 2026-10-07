from apps import apps_types
from apps.web.logger import get_logger
from apps.web.security import hash_refresh_token

from .uow import AbstractUserUnitOfWork


class LogoutCommandHandler:
    """Обработчик команды выхода: отзыв refresh-токена."""

    def __init__(self, unit_of_work: AbstractUserUnitOfWork) -> None:
        """
        Конструктор обработчика выхода.

        Args:
            unit_of_work: Объект шаблона Единица работы.
        """
        self._uow = unit_of_work
        self._logger = get_logger()

    async def handle(self, user_uid: apps_types.UserUID, refresh_token: str) -> None:
        """
        Отозвать refresh-токен пользователя. Access-токен не отзывается и действует до истечения срока.

        Идемпотентно: уже отозванный, истёкший, неизвестный или чужой токен — не ошибка (ответ тот же,
        чтобы не раскрывать, существует ли токен); чужой токен при этом не отзывается.

        Args:
            user_uid: Пользователь из access-токена.
            refresh_token: Открытое значение refresh-токена.
        """
        async with self._uow as uow:
            token = await uow.refresh_token_repo.get_by_hash_for_update(hash_refresh_token(refresh_token))
            if token is None or not token.belongs_to(user_uid) or token.revoked:
                self._logger.info("Выход пользователя %s: токен не найден, чужой или уже отозван", user_uid)
                return
            token.revoke()
            await uow.refresh_token_repo.update(token)
            await uow.commit()
        self._logger.info("Выход пользователя %s", user_uid)
