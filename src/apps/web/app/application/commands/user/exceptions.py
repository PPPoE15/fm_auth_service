from apps.web.app.utils.exceptions import BaseBadRequestError, BaseNotFoundError, BaseUnauthorizedError


class UserAlreadyExistsError(BaseNotFoundError):
    """Пользователь уже существует"""


class PasswordConfirmationError(BaseBadRequestError):
    """Пароли не совпадают"""


class UnauthorizedError(BaseUnauthorizedError):
    """Ошибка авторизации."""
