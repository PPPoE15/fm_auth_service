from pydantic import Field
from starlette import status

from . import base


class ConflictErrorResponseSchema(base.BaseErrorResponseSchema):
    """Модель ответа о конфликте с текущим состоянием ресурса в соответствии с RFC7807."""

    type: str = Field(
        title="URI",
        description="Ссылка на документацию",
        examples=["/help-center?helpSectionId=errors#409"],
        default="/help-center?helpSectionId=errors#409",
    )
    title: str = Field(
        title="Ответ (описание)",
        description="Описание HTTP-кода ответа",
        max_length=256,
        examples=["Conflict"],
        default="Conflict",
    )
    status: int = Field(
        title="Ответ (код)",
        description="Число, строго соответствует HTTP-коду ответа",
        examples=[status.HTTP_409_CONFLICT],
        default=status.HTTP_409_CONFLICT,
    )
    detail: str = Field(
        title="Информация",
        description="Интернационализируемое описание ошибки",
        examples=["Ресурс уже существует"],
        default="Ресурс уже существует",
    )
    code: str = Field(
        title="Внутренний код ошибки",
        description="Числобуквенный код ошибки в рамках продукта FM",
        examples=["FM-409000"],
        default="FM-409000",
    )
