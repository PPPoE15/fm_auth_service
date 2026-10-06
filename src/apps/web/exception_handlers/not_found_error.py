from pydantic import Field
from starlette import status

from . import base


class NotFoundErrorResponseSchema(base.BaseErrorResponseSchema):
    """Модель ответа об ошибке авторизации в соответствии с RFC7807."""

    type: str = Field(
        title="URI",
        description="Ссылка на документацию",
        examples=["/help-center?helpSectionId=errors#404"],
        default="/help-center?helpSectionId=errors#404",
    )
    title: str = Field(
        title="Ответ (описание)",
        description="Описание HTTP-кода ответа",
        max_length=256,
        examples=["Resource not found"],
        default="Resource not found",
    )
    status: int = Field(
        title="Ответ (код)",
        description="Число, строго соответствует HTTP-коду ответа",
        examples=[status.HTTP_404_NOT_FOUND],
        default=status.HTTP_404_NOT_FOUND,
    )
    detail: str = Field(
        title="Информация",
        description="Интернациолизируемое описание ошибки",
        examples=["Ресурс не найден"],
        default="Ресурс не найден",
    )
    code: str = Field(
        title="Внутренний код ошибки",
        description="Числобуквенный код ошибки в рамках продута FM",
        examples=["FM-404000"],
        default="FM-404000",
    )
