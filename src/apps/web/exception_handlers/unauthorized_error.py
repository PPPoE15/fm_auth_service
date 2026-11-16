from pydantic import Field
from starlette import status

from . import base


class UnauthorizedErrorResponseSchema(base.BaseErrorResponseSchema):
    """Модель ответа об ошибке авторизации в соответствии с RFC7807."""

    type: str = Field(
        title="URI",
        description="Ссылка на документацию",
        examples=["/help-center?helpSectionId=errors#401"],
        default="/help-center?helpSectionId=errors#401",
    )
    title: str = Field(
        title="Ответ (описание)",
        description="Описание HTTP-кода ответа",
        max_length=256,
        examples=["Unauthorized"],
        default="Unauthorized",
    )
    status: int = Field(
        title="Ответ (код)",
        description="Число, строго соответствует HTTP-коду ответа",
        examples=[status.HTTP_401_UNAUTHORIZED],
        default=status.HTTP_401_UNAUTHORIZED,
    )
    detail: str = Field(
        title="Информация",
        description="Интернациолизируемое описание ошибки",
        examples=["Неавторизованный запрос"],
        default="Неавторизованный запрос",
    )
    code: str = Field(
        title="Внутренний код ошибки",
        description="Числобуквенный код ошибки в рамках продукта FM",
        examples=["FM-401000"],
        default="FM-401000",
    )
