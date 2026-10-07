from apps.web.app.utils.datetime_tz import aware_now
from apps.web.logger import get_logger
from apps.web.security import hash_refresh_token

from .exceptions import InvalidRefreshTokenError
from .tokens import TokenIssuer, TokenPair
from .uow import AbstractUserUnitOfWork


class RefreshTokenCommandHandler:
    """Обработчик команды обновления пары токенов по refresh-токену (с ротацией)."""

    def __init__(
        self,
        unit_of_work: AbstractUserUnitOfWork,
        token_issuer: TokenIssuer,
    ) -> None:
        """
        Конструктор обработчика обновления токенов.

        Args:
            unit_of_work: Объект шаблона Единица работы.
            token_issuer: Выдача пары токенов.
        """
        self._uow = unit_of_work
        self._token_issuer = token_issuer
        self._logger = get_logger()

    async def handle(self, refresh_token: str) -> TokenPair:
        """
        Обменять действующий refresh-токен на новую пару; переданный токен отзывается.

        Args:
            refresh_token: Открытое значение refresh-токена.

        Raises:
            InvalidRefreshTokenError: Если токен неизвестен, истёк, отозван или его пользователя больше нет.
        """
        # NOTE(FM-16): строгая ротация без льготного окна (по контракту): если ответ потерялся после commit, у клиента
        # остаётся только отозванный токен, и повтор даёт FM-401002 — нужен повторный вход.
        msg = "Сессия истекла, войдите снова"
        async with self._uow as uow:
            used_token = await uow.refresh_token_repo.get_by_hash_for_update(hash_refresh_token(refresh_token))
            # TODO(FM-16): повторное предъявление уже ротированного токена (признак кражи) не отзывает остальные
            # токены пользователя — нужна цепочка (family) и её отзыв целиком; контрактом не требуется.
            if used_token is None or not used_token.is_active(aware_now()):
                raise InvalidRefreshTokenError(msg)
            used_token.revoke()
            await uow.refresh_token_repo.update(used_token)
            user = await uow.user_repo.get_by_uid(used_token.user_uid)
            # NOTE(FM-16): в Postgres недостижимо — токены удаляются вместе с пользователем (ON DELETE CASCADE);
            # защитная проверка, в тестах покрыта только на репозитории в памяти.
            if user is None:
                raise InvalidRefreshTokenError(msg)
            token_pair = await self._token_issuer.issue(uow, user)
            await uow.commit()
        self._logger.info("Обновлена сессия пользователя %s", user.uid)
        return token_pair
