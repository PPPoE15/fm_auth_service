from apps.shared.exceptions import BaseConflictError, BaseCustomValidationError


class UserAlreadyExistsError(BaseConflictError):
    """Пользователь уже существует"""

    code = "FM-409001"


class PasswordConfirmationError(BaseCustomValidationError):
    """Пароли не совпадают"""

    code = "FM-400001"
    field = "password_confirmation"
