"""Проверить состав готового образа: python scripts/check-image.py dev|master."""

import importlib
import importlib.util
import shutil
import sys
from pathlib import Path


def check_image(target: str) -> None:
    """Проверить runtime-зависимости, средства отладки и отсутствие сборочного мусора."""
    for module in ("asyncpg", "sqlalchemy", "alembic", "fastapi", "jwt", "cryptography", "argon2", "passlib", "uvicorn"):
        importlib.import_module(module)
    from passlib.context import CryptContext

    context = CryptContext(schemes=["argon2"])
    hashed = context.hash("FM-67 runtime probe")
    assert context.verify("FM-67 runtime probe", hashed), "Не работает Argon2"
    for executable in ("poetry", "gcc", "g++", "cc", "make"):
        assert shutil.which(executable) is None, f"Лишний инструмент: {executable}"
    assert importlib.util.find_spec("poetry") is None, "Poetry попал в окружение приложения"
    for module in ("debugpy", "pytest", "mypy", "ruff"):
        installed = importlib.util.find_spec(module) is not None
        assert installed == (target == "dev"), f"Неверный состав {target}: {module}"
    for directory in ("/root/.cache/pip", "/root/.cache/pypoetry", "/var/lib/apt/lists"):
        path = Path(directory)
        assert not path.exists() or not any(path.iterdir()), f"Остался кэш: {directory}"
    assert shutil.which("bash"), "Нет shell для entrypoint"
    print(f"Состав {target}: OK")


if __name__ == "__main__":
    assert sys.argv[1:] in (["dev"], ["master"]), "Укажите dev или master"
    check_image(sys.argv[1])
