from fastapi import FastAPI

from apps.shared.exceptions import (
    BaseBadRequestError,
    BaseConflictError,
    BaseForbiddenError,
    BaseNotFoundError,
    BaseUnauthorizedError,
)
from apps.web.exception_handlers.bad_request_error import BadRequestErrorResponseSchema
from apps.web.exception_handlers.base import register_error_handler
from apps.web.exception_handlers.conflict_error import ConflictErrorResponseSchema
from apps.web.exception_handlers.forbidden_error import ForbiddenErrorResponseSchema
from apps.web.exception_handlers.not_found_error import NotFoundErrorResponseSchema
from apps.web.exception_handlers.server_error import setup_server_exception_handlers
from apps.web.exception_handlers.unauthorized_error import UnauthorizedErrorResponseSchema
from apps.web.exception_handlers.validation_error import setup_validation_exception_handlers


def setup(app: FastAPI) -> None:
    """
    Настройка обработчиков внутренних ошибок.

    Args:
        app: Приложение FastAPI.
    """
    # TODO(FM-19): ошибки разбора тела в Starlette (невалидный UTF-8, слишком длинное число, глубокая вложенность)
    # отдают 400 {"detail": ...} не в формате RFC 7807 и без code; нужен обработчик HTTPException. Было до FM-15.
    setup_server_exception_handlers(app)
    setup_validation_exception_handlers(app)
    register_error_handler(app, BaseUnauthorizedError, UnauthorizedErrorResponseSchema)
    register_error_handler(app, BaseForbiddenError, ForbiddenErrorResponseSchema)
    register_error_handler(app, BaseNotFoundError, NotFoundErrorResponseSchema)
    register_error_handler(app, BaseBadRequestError, BadRequestErrorResponseSchema)
    register_error_handler(app, BaseConflictError, ConflictErrorResponseSchema)
