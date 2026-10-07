from apps.web.app.utils.exceptions import BaseConflictError, BaseCustomValidationError, BaseUnauthorizedError


class UserAlreadyExistsError(BaseConflictError):
    """Пользователь уже существует"""

    code = "FM-409001"


class PasswordConfirmationError(BaseCustomValidationError):
    """Пароли не совпадают"""

    code = "FM-400001"
    field = "password_confirmation"


class InvalidCredentialsError(BaseUnauthorizedError):
    """Неверный email или пароль (какое из двух — не раскрывается)."""

    code = "FM-401001"


class InvalidRefreshTokenError(BaseUnauthorizedError):
    """Refresh-токен неизвестен, истёк или отозван."""

    code = "FM-401002"
