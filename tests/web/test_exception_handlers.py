import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.shared.exceptions import (
    BaseBadRequestError,
    BaseConflictError,
    BaseError,
    BaseForbiddenError,
    BaseNotFoundError,
    BaseUnauthorizedError,
)
from apps.web.main import build_app

BASE_ERRORS: list[tuple[type[BaseError], int]] = [
    (BaseBadRequestError, 400),
    (BaseUnauthorizedError, 401),
    (BaseForbiddenError, 403),
    (BaseNotFoundError, 404),
    (BaseConflictError, 409),
]


def _app_raising(error: BaseError) -> FastAPI:
    fastapi_app = build_app()

    @fastapi_app.get("/test/error")
    async def raise_error() -> None:
        raise error

    return fastapi_app


@pytest.mark.parametrize(("base_error", "status_code"), BASE_ERRORS)
def test_handler_returns_default_code_of_status(base_error: type[BaseError], status_code: int) -> None:
    with TestClient(_app_raising(base_error("Ошибка"))) as client:
        response = client.get("/test/error")

    assert response.status_code == status_code
    assert response.json()["code"] == f"FM-{status_code}000"
    assert response.json()["detail"] == "Ошибка"
    assert response.json()["instance"] == "/test/error"


@pytest.mark.parametrize(("base_error", "status_code"), BASE_ERRORS)
def test_handler_returns_code_of_specific_error(base_error: type[BaseError], status_code: int) -> None:
    specific_error = type("SpecificError", (base_error,), {"code": f"FM-{status_code}777"})

    with TestClient(_app_raising(specific_error("Ошибка"))) as client:
        response = client.get("/test/error")

    assert response.status_code == status_code
    assert response.json()["code"] == f"FM-{status_code}777"
