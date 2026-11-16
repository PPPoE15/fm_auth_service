from apps.shared.exceptions import BaseUnauthorizedError


class InvalidCredentialsError(BaseUnauthorizedError):
    """Неверный email или пароль (какое из двух — не раскрывается)."""

    code = "FM-401001"


class InvalidRefreshTokenError(BaseUnauthorizedError):
    """Refresh-токен неизвестен, истёк или отозван."""

    code = "FM-401002"
