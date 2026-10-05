from apps.web.app.utils.exceptions import BaseBadRequestError, BaseConflictError, BaseUnauthorizedError


class UserAlreadyExistsError(BaseConflictError):
    """Пользователь уже существует"""

    code = "FM-409001"


class PasswordConfirmationError(BaseBadRequestError):
    """Пароли не совпадают"""


class UnauthorizedError(BaseUnauthorizedError):
    """Ошибка авторизации."""
