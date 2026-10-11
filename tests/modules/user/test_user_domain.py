from datetime import UTC, datetime

from apps.modules.user import User


def _user(name: str | None = None) -> User:
    return User.create(
        name=name,
        password_hash="hash",
        email="name@example.com",
        created_date=datetime(2026, 10, 11, tzinfo=UTC),
    )


def test_user_can_be_created_without_name() -> None:
    assert _user().name is None


def test_rename_sets_name() -> None:
    user = _user()

    user.rename("Артём")

    assert user.name == "Артём"


def test_rename_replaces_existing_name() -> None:
    user = _user("Артём")

    user.rename("Другое имя")

    assert user.name == "Другое имя"
