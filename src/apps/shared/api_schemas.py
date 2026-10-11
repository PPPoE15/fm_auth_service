from typing import Generic, TypeVar

from pydantic import ConfigDict, Field

from apps.shared.schemas import Base

DataT = TypeVar("DataT")


class BaseResponseSchema(Base, Generic[DataT]):
    """Базовый класс ответа с одним элементом для API."""

    content: DataT


class BaseListResponseSchema(Base, Generic[DataT]):
    """Базовый класс ответа со списком для API."""

    total: int = Field(
        title="Общее количество элементов в БД",
        description="Общее количество элементов в БД",
        examples=[100],
    )
    content: list[DataT]


class RequestBase(Base):
    """База схем тела запроса: неизвестные поля отклоняются (422)."""

    model_config = ConfigDict(extra="forbid")
