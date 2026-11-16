from pydantic import Field
from starlette import status

from . import base


class ForbiddenErrorResponseSchema(base.BaseErrorResponseSchema):
    """Модель ответа об ошибке доступа в соответствии с RFC7807."""

    type: str = Field(
        title="URI",
        description="Ссылка на документацию",
        examples=["/help-center?helpSectionId=errors#403"],
        default="/help-center?helpSectionId=errors#403",
    )
    title: str = Field(
        title="Ответ (описание)",
        description="Описание HTTP-кода ответа",
        max_length=256,
        examples=["Forbidden"],
        default="Forbidden",
    )
    status: int = Field(
        title="Ответ (код)",
        description="Число, строго соответствует HTTP-коду ответа",
        examples=[status.HTTP_403_FORBIDDEN],
        default=status.HTTP_403_FORBIDDEN,
    )
    detail: str = Field(
        title="Информация",
        description="Интернационализируемое описание ошибки",
        examples=["Доступ запрещен"],
        default="Доступ запрещен",
    )
    code: str = Field(
        title="Внутренний код ошибки",
        description="Числобуквенный код ошибки в рамках продукта",
        examples=["FM-403000"],
        default="FM-403000",
    )
