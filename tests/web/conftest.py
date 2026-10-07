from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from apps import apps_types
from apps.web.app.aggregators.models import User
from apps.web.app.handlers.api.user import deps
from apps.web.main import build_app
from apps.web.security import UserInfo, get_user_info
from tests.conftest import InMemoryUserUnitOfWork, RefreshTokensStorage


@pytest.fixture
def app(
    users_storage: dict[apps_types.UserUID, User],
    refresh_tokens_storage: RefreshTokensStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> FastAPI:
    """Приложение сервиса с хранилищами в памяти и тестовым защищённым эндпоинтом."""
    monkeypatch.setattr(
        deps,
        "UserUnitOfWork",
        lambda **_: InMemoryUserUnitOfWork(users_storage, refresh_tokens_storage),
    )
    fastapi_app = build_app()

    @fastapi_app.get("/test/protected")
    async def protected(user_info: UserInfo = Depends(get_user_info)) -> dict[str, Any]:
        return {"uid": str(user_info.uid)}

    return fastapi_app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
