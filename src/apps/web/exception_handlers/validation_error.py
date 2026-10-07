from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette import status

from apps.web.app.utils.exceptions import BaseCustomValidationError

from . import base

# Значения этих полей не возвращаются в ответе об ошибке валидации.
# TODO(FM-15): значения лишних полей (extra_forbidden) клиенту не нужны, но возвращаются — пароль под
# чужим ключом (например, passwordConfirmation) уйдёт в rejectedValue; для extra_forbidden отдавать None.
SENSITIVE_FIELDS = frozenset({"password", "password_confirmation", "refresh_token"})


class ValidationField(BaseModel):
    """Поле ошибки с детальной информацией"""

    message: str = Field(
        title="Сообщение",
        description="Текст ошибки валидации",
        examples=["Не должно быть пустым"],
    )
    field: str = Field(
        title="Поле в запросе",
        description="Название поля в запросе, на котором сработала валидация",
        examples=["card.surname"],
    )
    rejected_value: str | None = Field(
        title="Содержимое поля",
        description="Значение поля, не прошедшее валидацию",
        examples=["comment"],
        alias="rejectedValue",
    )
    rule: str = Field(
        title="Правило",
        description="Название правила валидации",
        examples=["NotEmpty"],
    )


class ValidationErrorResponseSchema(base.BaseErrorResponseSchema):
    """Модель ответа об ошибке валидации в соответствии с RFC7807."""

    type: str = Field(
        title="URI",
        description="Ссылка на документацию",
        examples=["/help-center?helpSectionId=errors#422"],
        default="/help-center?helpSectionId=errors#422",
    )
    title: str = Field(
        title="Ответ (описание)",
        description="Описание HTTP-кода ответа",
        max_length=256,
        examples=["Bad Request"],
        default="Bad Request",
    )
    status: int = Field(
        title="Ответ (код)",
        description="Число, строго соответствует HTTP-коду ответа",
        examples=[status.HTTP_422_UNPROCESSABLE_ENTITY],
        default=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
    detail: str = Field(
        title="Информация",
        description="Интернациолизируемое описание ошибки",
        examples=["Валидация не пройдена"],
        default="Валидация не пройдена",
    )
    validation: list[ValidationField] = Field(
        title="Ошибки валидации",
        description="Список ошибок форматной валидации",
    )
    code: str = Field(
        title="Внутренний код ошибки",
        description="Числобуквенный код ошибки в рамках продута FM",
        examples=["FM-422000"],
        default="FM-422000",
    )


def _rejected_value(body: Any, loc: tuple[int | str, ...]) -> str | None:  # noqa: ANN401
    """
    Значение поля из тела запроса для ответа об ошибке валидации.

    Сырое тело (строка — например, битый JSON) и значения паролей не возвращаются никогда.

    Args:
        body: Разобранное тело запроса.
        loc: Путь к полю внутри тела.
    """
    if not loc or not isinstance(body, dict | list) or loc[0] in SENSITIVE_FIELDS:
        return None
    value = base.get_body_info(body, loc)
    if value is None:
        return None
    # Одиночные суррогаты (\ud800) проходят json.loads, но не кодируются в UTF-8 при отправке ответа.
    # TODO(FM-15): не строки отдаются как Python repr (True, {'a': 'b'}, inf);
    # для них использовать json.dumps(ensure_ascii=False).
    return str(value).encode("utf-8", "replace").decode("utf-8")


def setup_validation_exception_handlers(app: FastAPI) -> None:
    """
    Настройка обработчиков ошибок валидации.

    Args:
        app: Приложение FastAPI.
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        error_validation = [
            ValidationField(
                message=err["msg"],
                field=".".join(str(part) for part in err["loc"][1:]) or str(err["loc"][0]),
                rejectedValue=_rejected_value(exc.body, tuple(err["loc"][1:])),
                rule=err["type"],
            )
            for err in exc.errors()
        ]
        error_correct_form = ValidationErrorResponseSchema(
            instance=request.url.path,
            validation=error_validation,
        )

        return error_correct_form.json_response()

    @app.exception_handler(BaseCustomValidationError)
    async def custom_validation_exception_handler(request: Request, exc: BaseCustomValidationError) -> JSONResponse:
        validation = []
        if exc.field:
            validation.append(
                ValidationField(message=exc.msg, field=exc.field, rejectedValue=None, rule="value_error"),
            )
        # TODO(FM-15): наследник без собственного code получит FM-422000 при статусе 400; задать код по умолчанию
        # FM-400000 и переиспользовать BaseErrorResponseSchema.from_error вместо ручной подстановки code.
        response = ValidationErrorResponseSchema(
            type="/help-center?helpSectionId=errors#400",
            instance=request.url.path,
            status=status.HTTP_400_BAD_REQUEST,
            detail=exc.msg,
            validation=validation,
        )
        if exc.code:
            response.code = exc.code
        return response.json_response()
