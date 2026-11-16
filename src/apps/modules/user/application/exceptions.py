from apps.shared.exceptions import BaseConflictError, BaseCustomValidationError, BaseUnauthorizedError


class UserAlreadyExistsError(BaseConflictError):
    """Пользователь уже существует"""

    code = "FM-409001"


class PasswordConfirmationError(BaseCustomValidationError):
    """Пароли не совпадают"""

    code = "FM-400001"
    field = "password_confirmation"


# NOTE(FM-15): отвечает так же, как InvalidTokenError (401, FM-401000) — для клиента это недействительная
# сессия.
class CurrentUserNotFoundError(BaseUnauthorizedError):
    """Пользователь из действительного токена не найден (например, удалён)."""
