import secrets
from functools import cache
from pathlib import Path
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, Field, ValidationError

from apps import apps_types
from apps.config import app_settings
from apps.web.app.utils.exceptions import BaseUnauthorizedError

_security_token = HTTPBearer(auto_error=False)


class SigningKeyError(RuntimeError):
    """Ключи подписи JWT отсутствуют или непригодны для настроенного алгоритма."""


class SigningKeyNotFoundError(SigningKeyError):
    """Файл ключа подписи JWT не найден."""


class InvalidTokenError(BaseUnauthorizedError):
    """Токен не передан, некорректен или истёк."""


class UserInfo(BaseModel):
    """Информация о пользователе."""

    uid: apps_types.UserUID = Field(description="Идентификатор пользователя.", alias="sub")


@cache
def _read_key(path: str) -> bytes:
    """
    Прочитать ключ подписи из файла (с кэшированием по пути).

    Кэш намеренный: при старте validate_signing_keys проверяет именно эти байты, и дальше
    сервис работает только с ними. Ротация ключей требует перезапуска сервиса.

    Args:
        path: Путь к файлу ключа.

    Raises:
        SigningKeyNotFoundError: Если файла нет.
    """
    try:
        return Path(path).read_bytes()
    except FileNotFoundError:
        msg = f"Не найден файл ключа подписи JWT: {path}"
        raise SigningKeyNotFoundError(msg) from None


def load_private_key() -> bytes:
    """Загрузить приватный ключ подписи JWT по пути из настроек."""
    return _read_key(app_settings.PRIVATE_KEY_PATH)


def load_public_key() -> bytes:
    """Загрузить публичный ключ проверки подписи JWT по пути из настроек."""
    return _read_key(app_settings.PUBLIC_KEY_PATH)


def validate_signing_keys() -> None:
    """
    Проверить ключи подписи JWT: файлы читаются, подходят к алгоритму и образуют пару.

    Вызывается при старте приложения, чтобы ошибка конфигурации ключей проявлялась сразу,
    а не ответом 500 на первом запросе.

    Raises:
        SigningKeyError: Если ключ не найден, не в формате PEM, не подходит к алгоритму
            или публичный ключ не соответствует приватному.
    """
    private_key = load_private_key()
    public_key = load_public_key()
    algorithm = app_settings.TOKEN_SIGNING_ALGORITHM
    try:
        probe_token = jwt.encode({"probe": True}, key=private_key, algorithm=algorithm)
        jwt.decode(probe_token, key=public_key, algorithms=[algorithm])
    except jwt.InvalidSignatureError:
        msg = (
            f"Публичный ключ {app_settings.PUBLIC_KEY_PATH} не соответствует "
            f"приватному ключу {app_settings.PRIVATE_KEY_PATH}"
        )
        raise SigningKeyError(msg) from None
    except (jwt.PyJWTError, NotImplementedError, TypeError, ValueError) as exc:
        msg = (
            f"Ключи подписи JWT ({app_settings.PRIVATE_KEY_PATH}, {app_settings.PUBLIC_KEY_PATH}) "
            f"непригодны для алгоритма {algorithm}: {exc}. Ожидаются ключи в формате PEM."
        )
        raise SigningKeyError(msg) from exc


async def _get_token(
    token: Annotated[HTTPAuthorizationCredentials | None, Depends(_security_token)],
) -> HTTPAuthorizationCredentials:
    """
    Извлечь JWT-токен из запроса.

    Raises:
        InvalidTokenError: Если токен не передан.
    """
    if token is None:
        msg = "Не авторизованный запрос!"
        raise InvalidTokenError(msg)
    return token


async def get_user_info(token: Annotated[HTTPAuthorizationCredentials, Depends(_get_token)]) -> UserInfo:
    """
    Извлечь из токена информацию о пользователе, проверив подпись и срок действия.

    Args:
        token: JWT-токен пользователя.

    Raises:
        InvalidTokenError: Если подпись неверна, токен истёк или некорректен.
    """
    try:
        payload = jwt.decode(
            token.credentials,
            key=load_public_key(),
            algorithms=[app_settings.TOKEN_SIGNING_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return UserInfo.model_validate(payload)
    except jwt.ExpiredSignatureError:
        msg = "Срок действия токена истёк!"
        raise InvalidTokenError(msg) from None
    except (jwt.InvalidTokenError, ValidationError):
        msg = "Некорректный токен!"
        raise InvalidTokenError(msg) from None


_pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    default="argon2",
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=1,
    bcrypt__rounds=12,
)


def hash_password(password: apps_types.Password) -> apps_types.PasswordHash:
    """Получить хэш пароля"""
    return _pwd_context.hash(password)


# TODO(FM-001.11): хеш считается лениво — первый вход с неизвестным email после рестарта медленнее;
# вычислять при старте (LifespanEvent). Время проверки старых bcrypt-хешей от него тоже отличается.
@cache
def dummy_password_hash() -> apps_types.PasswordHash:
    """Хеш случайного пароля для проверки при входе с неизвестным email (выравнивает время ответа)."""
    return hash_password(secrets.token_urlsafe(16))


def verify_password(plain_password: apps_types.Password, hashed_password: apps_types.PasswordHash) -> bool:
    """Проверить на совпадение пароль и его хэш."""
    return _pwd_context.verify(plain_password, hashed_password)
