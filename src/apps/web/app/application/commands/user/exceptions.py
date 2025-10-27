from apps.web.app.utils.exceptions import BaseBadRequestError, BaseNotFoundError


class UserAlreadyExistsError(BaseNotFoundError):
    """Пользователь уже существует"""


class PasswordConfirmationError(BaseBadRequestError):
    """Пароли не совпадают"""
