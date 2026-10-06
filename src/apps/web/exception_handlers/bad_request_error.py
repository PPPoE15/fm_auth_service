from pydantic import Field
from starlette import status

from . import base


class BadRequestErrorResponseSchema(base.BaseErrorResponseSchema):
    """Модель ответа о некорректном запросе в соответствии с RFC7807."""

    type: str = Field(
        title="URI",
        description="Ссылка на документацию",
        examples=["/help-center?helpSectionId=errors_web#400"],
        default="400",
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
        examples=[status.HTTP_400_BAD_REQUEST],
        default=status.HTTP_400_BAD_REQUEST,
    )
    detail: str = Field(
        title="Информация",
        description="Интернационализируемое описание ошибки",
        examples=["Некорректный запрос"],
        default="Некорректный запрос",
    )
    code: str = Field(
        title="Внутренний код ошибки",
        description="Числобуквенный код ошибки",
        examples=["FM-400000"],
        default="FM-400000",
    )
