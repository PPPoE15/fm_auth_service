from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Self, cast

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.status import (
    HTTP_400_BAD_REQUEST,
)

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

    from apps.shared.exceptions import BaseError

logger = logging.getLogger("default")


class BaseErrorResponseSchema(BaseModel):
    """Базовая модель ответа в соответствии с RFC7807."""

    type: str = Field(
        title="URI",
        description="Ссылка на документацию",
        examples=["/help-center?helpSectionId=errors#403"],
    )
    title: str = Field(
        title="Ответ (описание)",
        description="Описание HTTP-кода ответа",
        max_length=256,
        examples=["Bad Request"],
    )
    status: int = Field(
        title="Ответ (код)",
        description="Число, строго соответствует HTTP-коду ответа",
        examples=[HTTP_400_BAD_REQUEST],
    )
    detail: str = Field(
        title="Информация",
        description="Интернациолизируемое описание ошибки",
        examples=["Валидация не пройдена"],
    )
    instance: str = Field(
        title="Путь",
        description="Подпуть запроса",
        examples=["/cards"],
    )
    code: str = Field(
        title="Внутренний код ошибки",
        description="Числобуквенный код ошибки в рамках продута",
        examples=["FM-403000"],
    )
    trace: str | None = Field(
        title="traceID",
        description="ID в OpenTracing",
        examples=["18eb321f07f637f091ca2b3e4df91cbb"],
        default=None,
    )

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @classmethod
    def from_error(cls, request: Request, exc: BaseError) -> Self:
        """
        Построить ответ по доменной ошибке.

        Собственный код ошибки (BaseError.code) заменяет код по умолчанию для HTTP-статуса.

        Args:
            request: Запрос, при обработке которого возникла ошибка.
            exc: Доменная ошибка.
        """
        fields: dict[str, Any] = {"instance": request.url.path, "detail": exc.msg}
        if exc.code:
            fields["code"] = exc.code
        return cls.model_validate(fields)

    def json_response(self) -> JSONResponse:
        """Конвертировать ошибку в JSONResponse."""
        return JSONResponse(
            content=self.model_dump(mode="json", by_alias=True),
            status_code=self.status,
            headers={"Content-Type": "application/problem+json"},
        )


def register_error_handler(
    app: FastAPI,
    error_cls: type[BaseError],
    schema_cls: type[BaseErrorResponseSchema],
) -> None:
    """
    Зарегистрировать обработчик доменной ошибки, отвечающий по схеме RFC7807.

    Args:
        app: Приложение FastAPI.
        error_cls: Базовый класс доменной ошибки (обрабатываются и его наследники).
        schema_cls: Схема ответа с HTTP-статусом и кодом по умолчанию.
    """

    async def error_handler(request: Request, exc: Exception) -> JSONResponse:
        return schema_cls.from_error(request, cast("BaseError", exc)).json_response()

    app.add_exception_handler(error_cls, error_handler)


def get_body_info(exception_body: Any | None, pointer: tuple) -> str | None:  # noqa: ANN401
    """
    В зависимости от типа ошибки может изменяться тип exception_body.

    Ошибки наподобие JSONDecodeError имеют атрибут body типа str.
    В остальных случаях данный атрибут dict.
    """
    try:
        if isinstance(exception_body, str):
            return exception_body[pointer[0] :].strip("\n}")
        if isinstance(exception_body, dict) and len(pointer) != 0:
            result = exception_body.get(pointer[0])
            if len(pointer) > 1:
                result = get_body_info(result, pointer[1:])
            return result
        if isinstance(exception_body, list):
            return exception_body[pointer[0]]
    except Exception:
        logger.exception("An error occurred")
    return ""
